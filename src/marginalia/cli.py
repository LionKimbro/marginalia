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

import argparse
import ast
import fnmatch
import json
import os
import re
import sys
from pathlib import Path

from . import __version__


META_RE = re.compile(r"^\s*#\s*meta:\s*(.*)\s*$")
DEF_RE = re.compile(r"^\s*(async\s+def|def)\s+([A-Za-z_]\w*)\s*\(")
DECORATOR_RE = re.compile(r"^\s*@")
COMMENT_RE = re.compile(r"^\s*#")
BLANK_RE = re.compile(r"^\s*$")


# ----------------------------
# Data model (plain records)
# ----------------------------

def make_meta(raw, modules, threads, callers, flags):
    return {
        "raw": raw,
        "modules": modules,
        "threads": threads,
        "callers": callers,
        "flags": flags,
    }


def empty_meta():
    return make_meta(
        raw={},
        modules=[],
        threads=[],
        callers=None,
        flags=[],
    )


def meta_from_kv_string(kv_string):
    """
    Parse: "modules=db,conversation threads=main callers=1 flags=D#X"
    """
    raw = {}

    tokens = [t for t in kv_string.strip().split() if t]
    for tok in tokens:
        if "=" not in tok:
            key = tok.strip()
            if key:
                raw.setdefault(key, []).append("true")
            continue

        key, val = tok.split("=", 1)
        key = key.strip()
        val = val.strip()

        if not key:
            continue

        if val == "":
            vals = []
        else:
            vals = [v.strip() for v in val.split(",") if v.strip()]

        raw[key] = vals

    modules = raw.get("modules", [])
    threads = raw.get("threads", [])

    callers = None
    if "callers" in raw and raw["callers"]:
        c0 = raw["callers"][0]
        if c0 == "*":
            callers = "*"
        else:
            try:
                callers = int(c0)
            except ValueError:
                callers = c0

    flags_chars = []
    if "flags" in raw and raw["flags"]:
        if len(raw["flags"]) == 1 and len(raw["flags"][0]) > 1:
            flags_chars = list(raw["flags"][0])
        else:
            for entry in raw["flags"]:
                flags_chars.extend(list(entry))

    flags = sorted(set(flags_chars))

    return make_meta(
        raw=raw,
        modules=modules,
        threads=threads,
        callers=callers,
        flags=flags,
    )


def make_item(symbol, file, lineno, meta):
    return {
        "symbol": symbol,
        "file": file,
        "lineno": lineno,
        "meta": meta,
    }


def item_to_json_obj(item):
    m = item["meta"]
    return {
        "symbol": item["symbol"],
        "file": item["file"],
        "lineno": item["lineno"],
        "meta": {
            "raw": m["raw"],
            "modules": m["modules"],
            "threads": m["threads"],
            "callers": m["callers"],
            "flags": m["flags"],
        },
    }


# ----------------------------
# File discovery
# ----------------------------

DEFAULT_GLOBS = ["*.py", "*.pyw"]
DEFAULT_EXCLUDE_DIRS = {
    ".git", ".hg", ".svn", "__pycache__", ".tox",
    ".venv", "venv", "env", "build", "dist",
}


def iter_source_files(paths, include_globs, exclude_dirs):
    exclude_dirs = set(exclude_dirs)
    out = []

    def matches_globs(p):
        return any(fnmatch.fnmatch(p.name, g) for g in include_globs)

    for pstr in paths:
        p = Path(pstr)
        if not p.exists():
            continue

        if p.is_file():
            if matches_globs(p):
                out.append(p)
            continue

        for root, dirs, files in os.walk(p):
            dirs[:] = [d for d in dirs if d not in exclude_dirs]
            rootp = Path(root)
            for f in files:
                fp = rootp / f
                if matches_globs(fp):
                    out.append(fp)

    return sorted(set(out), key=lambda x: str(x).lower())


def normalize_path(path, base):
    try:
        if base:
            return str(path.resolve().relative_to(base.resolve())).replace("\\", "/")
    except Exception:
        pass
    return str(path.resolve()).replace("\\", "/")


# ----------------------------
# Parsing
# ----------------------------

def collect_function_def_lines(source_lines):
    src = "".join(source_lines)
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return {}

    lineno_to_name = {}

    class V(ast.NodeVisitor):
        def visit_FunctionDef(self, node):
            lineno_to_name[node.lineno] = node.name
            self.generic_visit(node)

        def visit_AsyncFunctionDef(self, node):
            lineno_to_name[node.lineno] = node.name
            self.generic_visit(node)

    V().visit(tree)
    return lineno_to_name


def extract_items_from_file(path, base):
    text = path.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines(keepends=True)

    lineno_to_name = collect_function_def_lines(lines)
    if not lineno_to_name:
        return []

    pending_meta = None
    items = []

    for idx, line in enumerate(lines, start=1):
        m = META_RE.match(line)
        if m:
            pending_meta = meta_from_kv_string(m.group(1))
            continue

        if BLANK_RE.match(line):
            continue
        if COMMENT_RE.match(line) and not DEF_RE.match(line):
            continue
        if DECORATOR_RE.match(line):
            continue

        if idx in lineno_to_name:
            name = lineno_to_name[idx]
            meta = pending_meta if pending_meta else empty_meta()
            items.append(
                make_item(
                    symbol=name,
                    file=normalize_path(path, base),
                    lineno=idx,
                    meta=meta,
                )
            )
            pending_meta = None
            continue

        pending_meta = None

    return items


# ----------------------------
# Outputs
# ----------------------------

def make_inventory(items):
    items = sorted(
        items,
        key=lambda it: (it["symbol"].lower(), it["file"].lower(), it["lineno"]),
    )
    return [item_to_json_obj(it) for it in items]


def make_indexes(items):
    items = sorted(
        items,
        key=lambda it: (it["symbol"].lower(), it["file"].lower(), it["lineno"]),
    )

    def sort_key(it):
        return (it["symbol"].lower(), it["file"].lower(), it["lineno"])

    by_symbol = {}
    for it in items:
        sym = it["symbol"]
        obj = item_to_json_obj(it)
        if sym not in by_symbol:
            by_symbol[sym] = obj
        else:
            if isinstance(by_symbol[sym], list):
                by_symbol[sym].append(obj)
            else:
                by_symbol[sym] = [by_symbol[sym], obj]

    def group_items(get_keys):
        buckets = {}
        for it in items:
            for k in get_keys(it):
                buckets.setdefault(k, []).append(it)

        out = {}
        for k, bucket in buckets.items():
            out[k] = [
                item_to_json_obj(b)
                for b in sorted(bucket, key=sort_key)
            ]
        return dict(sorted(out.items(), key=lambda kv: kv[0].lower()))

    return {
        "by-symbol": by_symbol,
        "by-file": group_items(lambda it: [it["file"]]),
        "by-module": group_items(lambda it: it["meta"]["modules"]),
        "by-thread": group_items(lambda it: it["meta"]["threads"]),
        "by-flag": group_items(lambda it: it["meta"]["flags"]),
    }


def dump_json(obj, pretty):
    if pretty:
        return json.dumps(obj, indent=2) + "\n"
    return json.dumps(obj, separators=(",", ":")) + "\n"


def write_destination(payload, dest):
    if dest == "stdout":
        sys.stdout.write(payload)
    else:
        Path(dest).write_text(payload, encoding="utf-8")


# ----------------------------
# CLI
# ----------------------------

def build_arg_parser():
    p = argparse.ArgumentParser(
        prog="marginalia",
        description="Marginalia — structured meta comments for Python code.",
    )

    sub = p.add_subparsers(dest="command", required=True)

    scan = sub.add_parser("scan", help="Scan Python source files.")
    indexes = sub.add_parser("indexes", help="Generate indexes from inventory.")

    scan.add_argument("paths", nargs="*", default=["."])
    scan.add_argument("--include", action="append", default=[])
    scan.add_argument("--exclude-dir", action="append", default=[])
    scan.add_argument("--base", default=None)

    scan.add_argument("--inventory", nargs="?", const="inventory.json")
    scan.add_argument("--indexes", nargs="?", const="indexes.json")
    scan.add_argument("--version", action="store_true")

    fmt = scan.add_mutually_exclusive_group()
    fmt.add_argument("--pretty", action="store_true")
    fmt.add_argument("--compact", action="store_true")

    indexes.add_argument("inventory_file")
    indexes.add_argument("--indexes", nargs="?", const="indexes.json")

    fmt2 = indexes.add_mutually_exclusive_group()
    fmt2.add_argument("--pretty", action="store_true")
    fmt2.add_argument("--compact", action="store_true")

    return p


def resolve_emits(args):
    if args.inventory is None and args.indexes is None:
        return {"inventory": "inventory.json", "indexes": "indexes.json"}

    emits = {}
    if args.inventory is not None:
        emits["inventory"] = args.inventory
    if args.indexes is not None:
        emits["indexes"] = args.indexes
    return emits


def run_scan_command(args):
    include_globs = DEFAULT_GLOBS + (args.include or [])
    exclude_dirs = DEFAULT_EXCLUDE_DIRS.union(set(args.exclude_dir or []))

    if args.base:
        base = Path(args.base)
    else:
        first = Path(args.paths[0]) if args.paths else Path(".")
        base = first if first.exists() and first.is_dir() else Path.cwd()

    files = iter_source_files(args.paths, include_globs, exclude_dirs)

    items = []
    for f in files:
        try:
            items.extend(extract_items_from_file(f, base))
        except Exception as e:
            sys.stderr.write(f"[marginalia] warning: failed to parse {f}: {e}\n")

    emits = resolve_emits(args)
    pretty = bool(args.pretty)

    if "inventory" in emits:
        write_destination(
            dump_json(make_inventory(items), pretty),
            emits["inventory"],
        )

    if "indexes" in emits:
        write_destination(
            dump_json(make_indexes(items), pretty),
            emits["indexes"],
        )

    return 0


def items_from_inventory(inventory):
    items = []
    for obj in inventory:
        meta = make_meta(
            raw=obj["meta"].get("raw", {}),
            modules=obj["meta"].get("modules", []),
            threads=obj["meta"].get("threads", []),
            callers=obj["meta"].get("callers"),
            flags=obj["meta"].get("flags", []),
        )
        items.append(
            make_item(
                symbol=obj["symbol"],
                file=obj["file"],
                lineno=obj["lineno"],
                meta=meta,
            )
        )
    return items


def run_indexes_command(args):
    inv_path = Path(args.inventory_file)
    if not inv_path.exists():
        sys.stderr.write(f"[marginalia] error: inventory not found: {inv_path}\n")
        return 1

    try:
        inventory_data = json.loads(inv_path.read_text(encoding="utf-8"))
    except Exception as e:
        sys.stderr.write(f"[marginalia] error: failed to read inventory: {e}\n")
        return 2

    try:
        items = items_from_inventory(inventory_data)
    except Exception as e:
        sys.stderr.write(f"[marginalia] error: invalid inventory format: {e}\n")
        return 3

    payload = dump_json(make_indexes(items), bool(args.pretty))
    write_destination(payload, args.indexes or "indexes.json")
    return 0


def main(argv=None):
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    if getattr(args, "version", False):
        print(f"marginalia {__version__}")
        return 0

    if args.command == "scan":
        return run_scan_command(args)
    if args.command == "indexes":
        return run_indexes_command(args)

    parser.error("No command specified")


if __name__ == "__main__":
    raise SystemExit(main())
