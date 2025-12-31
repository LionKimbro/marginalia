# marginalia/indexes_command.py
import json

from .errors import UsageError, MetaParseError, StrictFailure, IoFailure
from .io_utils import write_json, stderr, dump_json
from .indexes import build_indexes
from .item_shape import validate_inventory_item_strict
from .state import db, g


# meta: modules=cli callers=cli.main
def run_indexes_command():
    try:
        return _run_indexes_command()
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

def _run_indexes_command():
    args = g["args"]
    if args.pretty and args.compact:
        raise UsageError("cannot combine --pretty and --compact")

    inv_path = args.inventory_file

    with open(inv_path, "r", encoding="utf-8") as f:
        inv = json.load(f)

    if not isinstance(inv, list):
        raise MetaParseError("inventory must be a JSON array")

    # initialize globals
    g["command"] = "indexes"
    g["paths"] = [inv_path]
    g["formatting_options"] = {"pretty": bool(args.pretty), "compact": bool(args.compact)}

    db[:] = []
    for item in inv:
        validate_inventory_item_strict(item)
        db.append(item)

    idx_obj = build_indexes(indexes_only=None)

    # routing
    dest = _route_one(args.indexes, "indexes.json")

    if dest == "stdout":
        s = dump_json(idx_obj, pretty=bool(args.pretty), compact=(bool(args.compact) or (not args.pretty)))
        if args.pretty:
            s += "\n"
        print(s, end="")
        return 0

    write_json(dest, idx_obj, pretty=bool(args.pretty), compact=(bool(args.compact) or (not args.pretty)))
    return 0

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
