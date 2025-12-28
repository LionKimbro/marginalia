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


RESERVED = {"modules", "threads", "callers", "flags"}


# meta: modules=scan callers=scan.scan_file
def is_meta_line(line):
    return META_RE.match(line) is not None

# meta: modules=scan callers=scan.scan_file
def parse_meta_line(line):
    m = META_RE.match(line)
    if not m:
        raise MetaParseError("not a meta line")

    body = (m.group(1) or "").strip()
    if not body:
        # valid but empty meta comment
        return {"anchor": None, "kv": {}}

    parts = body.split()
    anchor = None
    kv = {}

    for part in parts:
        if part.startswith("@"):
            am = ANCHOR_TOKEN_RE.match(part)
            if not am:
                raise MetaParseError(f"bad anchor token: {part}")
            anchor = am.group(1)
            continue

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

        kv[k] = vals  # last wins

    return {"anchor": anchor, "kv": kv}

# meta: modules=scan callers=scan.scan_file
def find_bindable(line):
    # returns (symbol, symbol_type) or (None, None)
    m = DEF_RE.match(line)
    if m:
        return m.group(2), "function"
    m = CLASS_RE.match(line)
    if m:
        return m.group(1), "class"
    m = DATA_RE.match(line)
    if m:
        return m.group(1), "data"
    return None, None

# meta: modules=scan callers=scan.scan_file
def should_skip_for_binding(line):
    if BLANK_RE.match(line):
        return True
    if COMMENT_RE.match(line) and not is_meta_line(line):
        return True
    if DECORATOR_RE.match(line):
        return True
    return False
