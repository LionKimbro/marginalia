# marginalia/scan_command.py
import os

from .discovery import iter_source_files
from .errors import UsageError, MetaParseError, StrictFailure, IoFailure
from .io_utils import write_json, stderr, dump_json
from .indexes import build_indexes
from .paths import is_dir, is_file, abspath, dirname
from .state import db, g
from .scan import scan_file

# meta: modules=cli,scan callers=cli.main
def run_scan_command(args):
    try:
        return _run_scan_command(args)
    except UsageError as e:
        stderr(f"marginalia: usage error: {e}")
        return 1
    except MetaParseError as e:
        stderr(f"marginalia: meta parse error: {e}")
        return 2
    except StrictFailure as e:
        stderr(f"marginalia: strict failure: {e}")
        return 3
    except OSError as e:
        stderr(f"marginalia: io error: {e}")
        return 4
    except Exception as e:
        stderr(f"marginalia: error: {e}")
        return 4


def _run_scan_command(args):
    if args.pretty and args.compact:
        raise UsageError("cannot combine --pretty and --compact")

    # base dir heuristic: if path is dir, use it; else cwd
    root = args.path
    if is_dir(root):
        base_dir = abspath(root)
    else:
        base_dir = abspath(os.getcwd())

    # discover files
    files = list(iter_source_files(root, files_glob=args.files, exclude_glob=args.exclude))

    # initialize globals
    g.clear()
    g["command"] = "scan"
    g["paths"] = [root]
    g["include_globs"] = [args.files] if args.files else None
    g["exclude_dirs"] = None
    g["base_path"] = base_dir
    g["formatting_options"] = {"pretty": bool(args.pretty), "compact": bool(args.compact)}

    db[:] = []

    all_warnings = []
    for p in files:
        disp = os.path.relpath(p, base_dir)
        items, warnings = scan_file(p, disp)
        db.extend(items)
        all_warnings.extend(warnings)

    emit_inv, emit_idx = _decide_emits(args)
    inv_dest, idx_dest = _decide_dests(args, base_dir, emit_inv, emit_idx)

    if all_warnings and args.warn:
        for w in all_warnings:
            stderr("marginalia: warning: " + w)

    if all_warnings and args.strict:
        raise StrictFailure(f"{len(all_warnings)} warning(s) in strict mode")

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


def _decide_emits(args):
    inv_specified = args.inventory is not None
    idx_specified = args.indexes is not None
    if (not inv_specified) and (not idx_specified):
        return True, True
    return inv_specified, idx_specified


def _decide_dests(args, base_dir, emit_inv, emit_idx):
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
        inv_dest = _route_one(inv_opt, os.path.join(base_dir, "inventory.json"))
    if emit_idx:
        idx_dest = _route_one(idx_opt, os.path.join(base_dir, "indexes.json"))

    n_stdout = 0
    if inv_dest == "stdout":
        n_stdout += 1
    if idx_dest == "stdout":
        n_stdout += 1
    if n_stdout > 1:
        raise UsageError("At most one output may be routed to stdout per invocation.")

    return inv_dest, idx_dest


def _route_one(opt_value, default_path):
    if opt_value is None:
        return default_path
    if opt_value is True:
        return default_path
    if isinstance(opt_value, str) and opt_value == "stdout":
        return "stdout"
    if isinstance(opt_value, str):
        return opt_value
    return default_path


def _emit_one(dest, obj, pretty, compact):
    if dest == "stdout":
        s = dump_json(obj, pretty=pretty, compact=compact)
        if pretty:
            s += "\n"
        print(s, end="")
        return
    write_json(dest, obj, pretty=pretty, compact=compact)
