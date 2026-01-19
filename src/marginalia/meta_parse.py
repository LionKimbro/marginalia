# marginalia/meta_parse.py
import re

from .errors import MetaParseError


META_RE = re.compile(r"^\s*#\s*meta:\s*(.*)\s*$")

# bindables
DEF_RE = re.compile(r"^\s*(async\s+def|def)\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(")
CLASS_RE = re.compile(r"^\s*class\s+([A-Za-z_][A-Za-z0-9_]*)\s*[\(:]")
DATA_RE = re.compile(r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=")

DECORATOR_RE = re.compile(r"^\s*@")
BLANK_RE = re.compile(r"^\s*$")
COMMENT_RE = re.compile(r"^\s*#")


ANCHOR_TOKEN_RE = re.compile(r"^@([A-Za-z0-9_-]+)$")
KEY_RE = re.compile(r"^[A-Za-z0-9_-]+$")
# values are split by comma; each value must match these chars (meta spec)
VALUE_RE = re.compile(r"^[^\s]+$")


RESERVED = {
    "systems",
    "roles",
    "threads",
    "callers",
    "flags",
    "assign_type",
}


# meta: modules=scan callers=scan.scan_file
def is_meta_line(line):
    return META_RE.match(line) is not None


# meta: modules=scan callers=scan.scan_file
def parse_meta_line(line):
    """
    Parse a '# meta:' comment line into structural tokens and key/value groups.

    Returns:
      {
        "anchor": str | None,
        "item_id": str | None,
        "reserved": dict[str, list[str]],
        "custom": dict[str, list[str]],
      }
    """
    m = META_RE.match(line)
    if not m:
        raise MetaParseError("not a meta line")

    body = (m.group(1) or "").strip()
    if not body:
        return {
            "anchor": None,
            "item_id": None,
            "reserved": {},
            "custom": {},
        }

    parts = body.split()

    anchor = None
    item_id = None
    reserved = {}
    custom = {}

    for part in parts:
        # -------------------------
        # anchor token
        # -------------------------
        if part.startswith("@"):
            am = ANCHOR_TOKEN_RE.match(part)
            if not am:
                raise MetaParseError(f"bad anchor token: {part}")
            anchor = am.group(1)
            continue

        # -------------------------
        # id token
        # -------------------------
        if part.startswith("#"):
            if not part[1:]:
                raise MetaParseError("empty id token")
            item_id = part
            continue

        # -------------------------
        # key=value
        # -------------------------
        if "=" not in part:
            raise MetaParseError(f"bad entry (missing '='): {part}")

        k, v = part.split("=", 1)

        if not KEY_RE.match(k):
            raise MetaParseError(f"bad key: {k}")

        if v == "":
            vals = []
        else:
            vals = v.split(",")
            for x in vals:
                if x == "":
                    raise MetaParseError(f"empty value in: {part}")
                if not VALUE_RE.match(x):
                    raise MetaParseError(f"bad value: {x} in {part}")

        if k in RESERVED:
            reserved[k] = list(vals)   # last wins
        else:
            custom[k] = list(vals)     # last wins

    return {
        "anchor": anchor,
        "item_id": item_id,
        "reserved": reserved,
        "custom": custom,
    }


# meta: modules=scan callers=scan.scan_file
def find_bindable(line):
    """
    Identify a bindable symbol declaration.

    Returns:
      (symbol, symbol_type) or (None, None)

    symbol_type ∈ {"function", "class", "var"}
    """
    m = DEF_RE.match(line)
    if m:
        return m.group(2), "function"

    m = CLASS_RE.match(line)
    if m:
        return m.group(1), "class"

    m = DATA_RE.match(line)
    if m:
        return m.group(1), "var"

    return None, None
