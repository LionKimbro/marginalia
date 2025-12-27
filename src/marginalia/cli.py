#!/usr/bin/env python3
"""
Marginalia — structured meta comments for Python functions.

Meta comment form:

    # meta: modules=db,conversation threads=main callers=1 flags=D#X
    def foo(...):
        ...

Rules:
- A meta comment applies to the next function definition encountered (def or async def),
  skipping blank lines, other comments, and decorators.
- If multiple meta comments appear before a def, the last one wins.

Outputs:
- inventory.json: list of items
- indexes.json: dict with by-symbol, by-file, by-module, by-thread, by-flag
"""

from __future__ import annotations

import argparse
import ast
import fnmatch
import json
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple, Union

from . import __version__


META_RE = re.compile(r"^\s*#\s*meta:\s*(.*)\s*$")
DEF_RE = re.compile(r"^\s*(async\s+def|def)\s+([A-Za-z_]\w*)\s*\(")
DECORATOR_RE = re.compile(r"^\s*@")
COMMENT_RE = re.compile(r"^\s*#")
BLANK_RE = re.compile(r"^\s*$")


# ----------------------------
# Data model
# ----------------------------

@dataclass
class Meta:
    # Keep original tokens too, but provide normalized fields for known keys
    raw: Dict[str, List[str]]

    modules: List[str]
    threads: List[str]
    callers: Union[int, str, None]  # int or "*"
    flags: List[str]                # list of single-character strings, unique, stable-sorted

    @staticmethod
    def empty() -> "Meta":
        return Meta(raw={}, modules=[], threads=[], callers=None, flags=[])

    @staticmethod
    def from_kv_string(kv_string: str) -> "Meta":
        """
        Parse: "modules=db,conversation threads=main callers=1 flags=D#X"
        - tokens separated by whitespace
        - each token: key=value1,value2,...
        """
        raw: Dict[str, List[str]] = {}

        # Split on whitespace, but keep it simple: your spec uses space-separated tokens.
        tokens = [t for t in kv_string.strip().split() if t]
        for tok in tokens:
            if "=" not in tok:
                # tolerate "bare keys" by treating as key=true
                key = tok.strip()
                if key:
                    raw.setdefault(key, []).append("true")
                continue

            key, val = tok.split("=", 1)
            key = key.strip()
            val = val.strip()

            if not key:
                continue

            # Values are comma-separated; empty means empty list
            vals = [v.strip() for v in val.split(",")] if val != "" else []
            vals = [v for v in vals if v != ""]
            raw[key] = vals

        # Normalize known fields
        modules = raw.get("modules", [])
        threads = raw.get("threads", [])  # you chose "threads"
        callers: Union[int, str, None]
        if "callers" in raw and raw["callers"]:
            c0 = raw["callers"][0]
            if c0 == "*":
                callers = "*"
            else:
                try:
                    callers = int(c0)
                except ValueError:
                    # keep as string if user puts something weird; still preserve in raw
                    callers = c0
        else:
            callers = None

        # flags are set<char> — accept either:
        #   flags=D#X   (single token)
        #   flags=D,#,X (comma separated)
        flags_chars: List[str] = []
        if "flags" in raw and raw["flags"]:
            if len(raw["flags"]) == 1 and len(raw["flags"][0]) > 1:
                # treat as packed string of characters
                flags_chars = list(raw["flags"][0])
            else:
                # treat as list, but each entry may still be multi-char; split into chars
                for entry in raw["flags"]:
                    flags_chars.extend(list(entry))

        # unique, stable order: sorted by codepoint for predictability
        flags_unique = sorted(set(flags_chars))

        return Meta(
            raw=raw,
            modules=modules,
            threads=threads,
            callers=callers,
            flags=flags_unique,
        )


@dataclass
class Item:
    symbol: str
    file: str               # normalized, relative-ish path
    lineno: int             # 1-based
    meta: Meta

    def to_json_obj(self) -> Dict[str, Any]:
        return {
            "symbol": self.symbol,
            "file": self.file,
            "lineno": self.lineno,
            "meta": {
                "raw": self.meta.raw,
                "modules": self.meta.modules,
                "threads": self.meta.threads,
                "callers": self.meta.callers,
                "flags": self.meta.flags,
            },
        }


# ----------------------------
# File discovery (scope control)
# ----------------------------

DEFAULT_GLOBS = ["*.py", "*.pyw"]
DEFAULT_EXCLUDE_DIRS = {".git", ".hg", ".svn", "__pycache__", ".tox", ".venv", "venv", "env", "build", "dist"}


def iter_source_files(paths: List[str], include_globs: List[str], exclude_dirs: Iterable[str]) -> List[Path]:
    """
    Collect files from given paths. If a path is a directory, walk recursively.
    """
    exclude_dirs_set = set(exclude_dirs)
    out: List[Path] = []

    def matches_globs(p: Path) -> bool:
        name = p.name
        return any(fnmatch.fnmatch(name, g) for g in include_globs)

    for pstr in paths:
        p = Path(pstr)
        if not p.exists():
            continue
        if p.is_file():
            if matches_globs(p):
                out.append(p)
            continue

        # directory
        for root, dirs, files in os.walk(p):
            # prune dirs in-place
            dirs[:] = [d for d in dirs if d not in exclude_dirs_set]
            rootp = Path(root)
            for f in files:
                fp = rootp / f
                if matches_globs(fp):
                    out.append(fp)

    # stable ordering
    out = sorted(set(out), key=lambda x: str(x).lower())
    return out


def normalize_path(path: Path, base: Optional[Path]) -> str:
    try:
        if base:
            return str(path.resolve().relative_to(base.resolve())).replace("\\", "/")
    except Exception:
        pass
    return str(path.resolve()).replace("\\", "/")


# ----------------------------
# Parsing
# ----------------------------

def collect_function_def_lines(source_lines: List[str]) -> Dict[int, str]:
    """
    Use AST to find function definitions and map lineno -> function name.
    This avoids regex false positives (e.g., 'def' in strings).
    """
    src = "".join(source_lines)
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return {}

    lineno_to_name: Dict[int, str] = {}

    class V(ast.NodeVisitor):
        def visit_FunctionDef(self, node: ast.FunctionDef) -> Any:
            lineno_to_name[node.lineno] = node.name
            self.generic_visit(node)

        def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> Any:
            lineno_to_name[node.lineno] = node.name
            self.generic_visit(node)

    V().visit(tree)
    return lineno_to_name


def extract_items_from_file(path: Path, base: Optional[Path]) -> List[Item]:
    text = path.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines(keepends=True)

    lineno_to_name = collect_function_def_lines(lines)
    if not lineno_to_name:
        return []

    # We attach meta comments to the next *actual* def line.
    # We'll scan lines in order and watch for meta comments, then consume at def.
    pending_meta: Optional[Meta] = None
    items: List[Item] = []

    # For "def association", we check lineno_to_name via line number to avoid regex traps.
    for idx, line in enumerate(lines, start=1):
        m = META_RE.match(line)
        if m:
            pending_meta = Meta.from_kv_string(m.group(1))
            continue

        # Skip lines that shouldn't consume meta
        if BLANK_RE.match(line) or (COMMENT_RE.match(line) and not DEF_RE.match(line)):
            continue
        if DECORATOR_RE.match(line):
            continue

        # Is this a real function def line?
        if idx in lineno_to_name:
            name = lineno_to_name[idx]
            meta = pending_meta if pending_meta is not None else Meta.empty()
            items.append(Item(
                symbol=name,
                file=normalize_path(path, base),
                lineno=idx,
                meta=meta,
            ))
            pending_meta = None  # consumed
            continue

        # Any other non-skipped line breaks the "pending meta" chain.
        pending_meta = None

    return items


# ----------------------------
# Outputs
# ----------------------------

def make_inventory(items: List[Item]) -> List[Dict[str, Any]]:
    # Stable ordering: by symbol, then file, then lineno
    items_sorted = sorted(items, key=lambda it: (it.symbol.lower(), it.file.lower(), it.lineno))
    return [it.to_json_obj() for it in items_sorted]


def make_indexes(items: List[Item]) -> Dict[str, Any]:
    items_sorted = sorted(items, key=lambda it: (it.symbol.lower(), it.file.lower(), it.lineno))

    def sort_key(it: Item) -> Tuple[str, str, int]:
        return (it.symbol.lower(), it.file.lower(), it.lineno)

    by_symbol: Dict[str, Any] = {}
    for it in items_sorted:
        # If duplicates exist, store list (rare, but can happen across files)
        if it.symbol not in by_symbol:
            by_symbol[it.symbol] = it.to_json_obj()
        else:
            existing = by_symbol[it.symbol]
            if isinstance(existing, list):
                existing.append(it.to_json_obj())
            else:
                by_symbol[it.symbol] = [existing, it.to_json_obj()]

    def group_items(get_keys) -> Dict[str, List[Dict[str, Any]]]:
        g: Dict[str, List[Item]] = {}
        for it in items_sorted:
            keys = get_keys(it)
            for k in keys:
                g.setdefault(k, []).append(it)
        # convert and sort each bucket by symbol
        out: Dict[str, List[Dict[str, Any]]] = {}
        for k, bucket in g.items():
            out[k] = [b.to_json_obj() for b in sorted(bucket, key=sort_key)]
        # stable key ordering
        return dict(sorted(out.items(), key=lambda kv: kv[0].lower()))

    by_file = group_items(lambda it: [it.file])
    by_module = group_items(lambda it: it.meta.modules)
    by_thread = group_items(lambda it: it.meta.threads)
    by_flag = group_items(lambda it: it.meta.flags)

    return {
        "by-symbol": by_symbol,
        "by-file": by_file,
        "by-module": by_module,
        "by-thread": by_thread,
        "by-flag": by_flag,
    }


def dump_json(obj: Any, pretty: bool) -> str:
    if pretty:
        return json.dumps(obj, indent=2, sort_keys=False) + "\n"
    return json.dumps(obj, separators=(",", ":"), sort_keys=False) + "\n"


def write_destination(payload: str, dest: str) -> None:
    if dest == "stdout":
        sys.stdout.write(payload)
        return
    Path(dest).write_text(payload, encoding="utf-8")


# ----------------------------
# CLI contract
# ----------------------------

def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="marginalia",
        description="Parse Marginalia '# meta:' comments and emit JSON inventory/indexes.",
    )
    
    p.add_argument(
        "paths",
        nargs="*",
        default=["."],
        help="Files and/or directories to scan (default: current directory).",
    )

    # Scope control
    p.add_argument(
        "--include",
        action="append",
        default=[],
        help="Additional glob(s) to include (can repeat). Default includes: *.py, *.pyw",
    )
    p.add_argument(
        "--exclude-dir",
        action="append",
        default=[],
        help=f"Directory name(s) to exclude from recursive scans (can repeat). Defaults exclude: {', '.join(sorted(DEFAULT_EXCLUDE_DIRS))}",
    )
    p.add_argument(
        "--base",
        default=None,
        help="Base directory for relative paths in output (default: inferred as first path if it's a directory, else cwd).",
    )

    # Output selection: default is both inventory + indexes to FILES
    # Each flag can be used as:
    #   --inventory           -> inventory.json
    #   --inventory=foo.json  -> foo.json
    #   --inventory=stdout    -> stdout
    p.add_argument(
        "--inventory",
        nargs="?",
        const="inventory.json",
        default=None,
        help="Emit inventory output. Optional value sets destination (filename or 'stdout'). "
             "If provided without a value, uses 'inventory.json'.",
    )
    p.add_argument(
        "--indexes",
        nargs="?",
        const="indexes.json",
        default=None,
        help="Emit indexes output. Optional value sets destination (filename or 'stdout'). "
             "If provided without a value, uses 'indexes.json'.",
    )

    p.add_argument(
        "--version",
        action="store_true",
        help="Print Marginalia version and exit.",
    )

    fmt = p.add_mutually_exclusive_group()
    fmt.add_argument("--pretty", action="store_true", help="Pretty-print JSON output.")
    fmt.add_argument("--compact", action="store_true", help="Minified JSON output (default).")

    return p


def resolve_emits(args: argparse.Namespace) -> Dict[str, str]:
    """
    Decide what to emit and where, per your rules:

    - By default: emit BOTH, to files inventory.json and indexes.json.
    - If user supplies --inventory and/or --indexes, only emit those supplied,
      unless both supplied.

    Each destination may be a filename or 'stdout'.
    """
    inv = args.inventory
    idx = args.indexes

    if inv is None and idx is None:
        return {"inventory": "inventory.json", "indexes": "indexes.json"}

    emits: Dict[str, str] = {}
    if inv is not None:
        emits["inventory"] = inv
    if idx is not None:
        emits["indexes"] = idx
    return emits


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    include_globs = DEFAULT_GLOBS + (args.include or [])
    exclude_dirs = DEFAULT_EXCLUDE_DIRS.union(set(args.exclude_dir or []))

    if args.version:
        print(f"marginalia {__version__}")
        return 0
    
    # Base path for output filenames
    if args.base:
        base = Path(args.base)
    else:
        # heuristic: if first path is a directory, use it as base; else cwd
        first = Path(args.paths[0]) if args.paths else Path(".")
        base = first if first.exists() and first.is_dir() else Path.cwd()

    files = iter_source_files(args.paths, include_globs=include_globs, exclude_dirs=exclude_dirs)

    items: List[Item] = []
    for f in files:
        try:
            items.extend(extract_items_from_file(f, base=base))
        except Exception as e:
            # Keep going; you can tighten this later.
            sys.stderr.write(f"[marginalia] warning: failed to parse {f}: {e}\n")

    emits = resolve_emits(args)

    pretty = bool(args.pretty)
    # compact is default unless --pretty
    inventory_obj = None
    indexes_obj = None

    if "inventory" in emits:
        inventory_obj = make_inventory(items)
        write_destination(dump_json(inventory_obj, pretty=pretty), emits["inventory"])

    if "indexes" in emits:
        indexes_obj = make_indexes(items)
        write_destination(dump_json(indexes_obj, pretty=pretty), emits["indexes"])

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
