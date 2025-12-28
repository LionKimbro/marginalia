# marginalia/item_shape.py
from .errors import MetaParseError


# meta: modules=db callers=scan.scan_file
def make_item(symbol, symbol_type, source_file, line_number, raw, meta_kv):
    # Reserved keys:
    # - modules, threads: arrays, normalized lowercase, unique
    # - callers: array | "*" | integer
    # - flags: string set-of-chars unique
    #
    # All other keys go into custom as arrays of strings (no special normalization).
    modules = []
    threads = []
    callers = "*"
    flags = ""
    custom = {}

    for k, vals in meta_kv.items():
        if k == "modules":
            modules = _norm_list(vals)
        elif k == "threads":
            threads = _norm_list(vals)
        elif k == "flags":
            flags = _norm_flags(vals)
        elif k == "callers":
            callers = _parse_callers(vals)
        else:
            custom[k] = list(vals)

    item = {
        "symbol": symbol,
        "symbol_type": symbol_type,
        "source_file": source_file,
        "line_number": int(line_number),
        "raw": raw,
        "modules": modules,
        "threads": threads,
        "callers": callers,
        "flags": flags,
        "custom": custom,
    }
    return item


def _norm_list(vals):
    seen = set()
    out = []
    for v in vals:
        lv = v.lower()
        if lv in seen:
            continue
        seen.add(lv)
        out.append(lv)
    return out


def _norm_flags(vals):
    # vals is a list from "flags=a,b,c" (per meta grammar)
    # but output wants a single string as a set-of-chars
    s = "".join(vals)
    seen = set()
    out = []
    for ch in s:
        if ch in seen:
            continue
        seen.add(ch)
        out.append(ch)
    return "".join(out)


def _parse_callers(vals):
    if len(vals) == 0:
        return "*"
    if len(vals) == 1:
        v = vals[0]
        if v == "*":
            return "*"
        if _is_int(v):
            return int(v)
        return [v]
    # many -> list
    # (do not coerce ints here; treat as symbols)
    return list(vals)


def _is_int(s):
    if not s:
        return False
    for ch in s:
        if ch < "0" or ch > "9":
            return False
    return True


# meta: modules=db callers=indexes_command._run_indexes_command
def validate_inventory_item_strict(item):
    required = ["symbol", "symbol_type", "source_file", "line_number", "raw", "modules", "threads", "callers", "flags", "custom"]
    for k in required:
        if k not in item:
            raise MetaParseError(f"inventory missing field: {k}")

    extra = [k for k in item.keys() if k not in required]
    if extra:
        raise MetaParseError(f"inventory extra fields: {extra}")

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
