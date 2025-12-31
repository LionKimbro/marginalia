# marginalia/item_shape.py
from .errors import MetaParseError
from .state import g


# meta: modules=scan writers=scan.scan_file callers=scan.scan_file
def new_item():
    """
    Initialize a new item-under-construction.

    The item dict itself is the assembly surface; fields are populated
    incrementally and are guaranteed valid by construction.
    """
    g["item"] = item = {
        "id": None,            # resolved explicitly or derived later
        "symbol": None,
        "symbol_type": None,
        "source_file": None,   # string, relative to g["base_path"]
        "line_number": None,
        "raw": None,           # raw "# meta: ..." line
        "modules": [],
        "threads": [],
        "callers": "*",
        "flags": "",
        "custom": {},
    }
    return item



# meta: modules=db callers=indexes_command._run_indexes_command
def validate_inventory_item_strict(item):
    required = ["item_id", "symbol", "symbol_type", "source_file", "line_number", "raw", "modules", "threads", "callers", "flags", "custom"]
    for k in required:
        if k not in item:
            raise MetaParseError(f"inventory missing field: {k}")

    extra = [k for k in item.keys() if k not in required]
    if extra:
        raise MetaParseError(f"inventory extra fields: {extra}")

    if not isinstance(item["item_id"], string) and item["item_id"][0] != "#":
        raise MetaParseError("item_id must be string (starting with '#')")
    if item["symbol_type"] not in ("function", "class", "data", "anchor"):
        raise MetaParseError(f"bad symbol_type: {item['symbol_type']}")

    if not isinstance(item["modules"], list):
        raise MetaParseError("modules must be array")
    if not isinstance(item["threads"], list):
        raise MetaParseError("threads must be array")
    # callers: list | "*" | int
    c = item["callers"]
    if not (c == "*" or isinstance(c, int) or isinstance(c, list)):
        raise MetaParseError("callers must be array | '*' | integer")
    if not isinstance(item["flags"], str):
        raise MetaParseError("flags must be string")
    if not isinstance(item["custom"], dict):
        raise MetaParseError("custom must be object")
