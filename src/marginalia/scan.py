# marginalia/scan.py
import io

from . import state
from .state import g
from .file_nav import start_reading, read_line
from .errors import MetaParseError
from . import meta_parse
from . import item_shape


# meta: modules=scan callers=scan_command._run_scan_command
def scan_file(p):
    # Initialize file cursor
    start_reading(p)

    # Precompute display name once per file
    source_file = str(p.relative_to(g["base_path"]))

    while read_line():
        line = g["line"]

        # ------------------------------------------------------------
        # Skip non-meta lines
        # ------------------------------------------------------------
        if not meta_parse.is_meta_line(line):
            continue

        # ------------------------------------------------------------
        # Parse meta line
        # ------------------------------------------------------------
        try:
            parsed = meta_parse.parse_meta_line(line)
        except MetaParseError as e:
            raise MetaParseError(f"{source_file}:{g['line_num']}: {e}")

        # Start new item-under-construction
        item = item_shape.new_item()

        item["source_file"] = source_file
        item["raw"] = line

        meta_kv = parsed["kv"]
        anchor = parsed.get("anchor")
        meta_line_num = g["line_num"]

        # ------------------------------------------------------------
        # Immediate bind (anchor) vs. read-ahead
        # ------------------------------------------------------------
        if anchor:
            item["symbol"] = anchor
            item["symbol_type"] = "anchor"
            item["line_number"] = meta_line_num
        elif not bind_next_symbol():
            state.warnings.append(
                f"{source_file}:{meta_line_num}: meta comment unbound (next line not bindable)"
            )
            continue

        resolve_item_id(parsed.get("item_id"))
        apply_meta(meta_kv)
        state.db.append(item)

    # Just a little tidying up...
    g["item"] = None


# ------------------------------------------------------------
# Helpers
# ------------------------------------------------------------

def bind_next_symbol():
    """
    Advance until a bindable symbol is found or binding fails.
    Returns True if bound, False otherwise.
    """
    item = g["item"]
    while read_line():
        line = g["line"]

        if meta_parse.should_skip_for_binding(line):
            continue

        sym, stype = meta_parse.find_bindable(line)
        if sym:
            item["symbol"] = sym
            item["symbol_type"] = stype
            item["line_number"] = g["line_num"]
            return True

        # Not skippable, not bindable → fail binding
        return False

    # EOF before binding
    return False


def resolve_item_id(explicit_item_id):
    """
    Resolve item id exactly once.
    """
    item = g["item"]
    if explicit_item_id is not None:
        item["id"] = explicit_item_id
    else:
        item["id"] = f"{item['source_file']}.{item['symbol']}"


# meta: modules=scan callers=scan.scan_file
def apply_meta(meta_kv):
    """
    Apply parsed meta key/value pairs to the current item-under-construction.

    Mutates g["item"] in place.
    """
    item = g["item"]

    for k, vals in meta_kv.items():
        if k == "modules":
            item["modules"] = _norm_list(vals)
        elif k == "threads":
            item["threads"] = _norm_list(vals)
        elif k == "flags":
            item["flags"] = _norm_flags(vals)
        elif k == "callers":
            item["callers"] = _parse_callers(vals)
        else:
            item["custom"][k] = list(vals)

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
