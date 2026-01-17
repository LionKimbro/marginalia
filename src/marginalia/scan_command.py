# marginalia/scan_command.py
from pathlib import Path

from . import discovery

from .errors import UsageError, MetaParseError, StrictFailure, IoFailure
from .io_utils import write_json, stderr, dump_json
from .indexes import build_indexes
from .state import db, g, warnings
from .scan import scan_file


# meta: modules=cli,scan callers=cli.main
def run_scan_command():
    try:
        return _run_scan_command()
    except UsageError as e:
        stderr(f"marginalia: usage error: {e}", e)
        return 1
    except MetaParseError as e:
        stderr(f"marginalia: meta parse error: {e}", e)
        return 2
    except StrictFailure as e:
        stderr(f"marginalia: strict failure: {e}", e)
        return 3
    except OSError as e:
        stderr(f"marginalia: io error: {e}", e)
        return 4
    except Exception as e:
        stderr(f"marginalia: error: {e}", e)
        return 4


def _run_scan_command():
    args = g["args"]
    if args.pretty and args.compact:
        raise UsageError("cannot combine --pretty and --compact")

    # base dir heuristic: if path is dir, use it; else cwd
    root = Path(args.path)
    if root.is_dir():
        base_path = root.resolve()
    else:
        base_path = Path.cwd().resolve()

    # discover files (iter_source_files likely yields strings)
    files = list(discovery.iter_source_files())
    
    # initialize globals
    g["command"] = "scan"  # TODO-- PRESERVE THIS NOTE: we're getting rid of this, because it's all in args I believe
    g["paths"] = [str(root)]  # TODO-- PRESERVE: we might be getting rid of this; candidate for evaluation for removal
    g["include_globs"] = [args.files] if args.files else None  # TODO-- PRESERVE: might be getting rid of; candidate for removal
    g["exclude_dirs"] = None
    g["base_path"] = base_path

    db[:] = []

    for p in files:
        scan_file(p)

    # check for duplicate ids
    seen = {}
    for i, rec in enumerate(db):
        rid = rec.get("id")
        if not rid:
            continue

        if rid in seen:
            first_i = seen[rid]
            warnings.append(
                f"duplicate id '{rid}' in entries {first_i} and {i}"
            )
        else:
            seen[rid] = i

    # does the user want --inventory?  --indexes?  (default: both)
    emit_inv, emit_idx = _decide_emits()
    inv_dest, idx_dest = _decide_dests(emit_inv, emit_idx)

    if warnings and args.warn:
        for w in warnings:
            stderr("marginalia: warning: " + w)

    if warnings and args.strict:
        raise StrictFailure(f"{len(warnings)} warning(s) in strict mode")

    pretty = bool(args.pretty)
    compact = bool(args.compact) or (not args.pretty)

    # projection
    idx_obj = None
    if emit_idx:
        idx_obj = build_indexes(indexes_only=args.indexes_only)

    # emission
    if emit_inv:
        _emit_one(inv_dest, db, pretty, compact)
    if emit_idx:
        _emit_one(idx_dest, idx_obj, pretty, compact)

    return 0


def _decide_emits():
    args = g["args"]
    inv_specified = args.inventory is not None
    idx_specified = args.indexes is not None
    if (not inv_specified) and (not idx_specified):
        return True, True
    return inv_specified, idx_specified


def _decide_dests(emit_inv, emit_idx):
    args = g["args"]
    from .output_routing import decide_destinations, decide_scan_emits
    # re-use decision logic but keep scan’s emission rules local to this file
    inv_specified = args.inventory is not None
    idx_specified = args.indexes is not None
    if (not inv_specified) and (not idx_specified):
        # emitted by default; treat as not-specified so routing uses defaults
        inv_opt = None
        idx_opt = None
    else:
        inv_opt = args.inventory
        idx_opt = args.indexes

    # emulate routing rules:
    inv_dest = None
    idx_dest = None
    if emit_inv:
        inv_dest = _route_one(inv_opt, g["base_path"] / "inventory.json")
    if emit_idx:
        idx_dest = _route_one(idx_opt, g["base_path"] / "indexes.json")

    n_stdout = 0
    if inv_dest == "stdout":
        n_stdout += 1
    if idx_dest == "stdout":
        n_stdout += 1
    if n_stdout > 1:
        raise UsageError("At most one output may be routed to stdout per invocation.")

    return inv_dest, idx_dest


def _route_one(opt_value, default_path: Path):
    if opt_value is None or opt_value is True:
        # user provided nothing, or just --option-name
        return default_path
    if isinstance(opt_value, str):
        if opt_value == "stdout":
            # user provided stdout
            return "stdout"
        else:
            # user provided explicit output path
            return Path(opt_value)
    raise ValueError(f"invalid output option value: {opt_value!r}")


def _emit_one(dest, obj, pretty, compact):
    if dest == "stdout":
        s = dump_json(obj, pretty=pretty, compact=compact)
        if pretty:
            s += "\n"
        print(s, end="")
        return
    write_json(dest, obj, pretty=pretty, compact=compact)
