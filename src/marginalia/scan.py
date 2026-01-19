# marginalia/scan.py
import io

from . import state, paths, events, flowctl, meta_parse, note_shape
from .state import g
from .file_nav import start_reading, read_line
from .errors import MetaParseError


# meta: modules=scan callers=scan_command._run_scan_command
def scan_file(p):
    """
    Streaming scan with an in-note accumulator (comment-spec v0.2 + note-spec v0.1):

    - The note under construction IS the accumulator: g["note"].
    - Both # meta: and # doc: lines can start a note.
    - raw: list of exact original # meta / # doc lines (no trailing newline).
    - doc: list of strings (payload after "# doc:").
    - Drain events:
        * meta line containing @anchor => drain immediately into anchor note (create-or-merge)
        * bindable symbol line         => drain into that symbol note
    - EOF with undrained note => orphaned metadata (halt or warn per fail_policy).
    """
    # Initialize file cursor
    start_reading(p)

    # Precompute display name once per file
    source_file = str(p)

    while read_line():
        line = g["line"]

        # ------------------------------------------------------------
        # DOC channel
        # ------------------------------------------------------------
        if _is_doc_line():
            _ensure_note()
            _acc_doc_line()
            continue

        # ------------------------------------------------------------
        # META channel
        # ------------------------------------------------------------
        if meta_parse.is_meta_line(line):
            try:
                parsed = meta_parse.parse_meta_line(line)
            except MetaParseError as e:
                events.append_event("meta-parse-error-on-line", {"e": e})
                flowctl.maybe_halt("meta parse error")
            
            _ensure_note()
            _acc_raw_line()

            # Merge parsed meta into the note-under-construction
            _acc_merge_reserved(parsed["reserved"])
            _acc_merge_custom(parsed["custom"])

            # Optional explicit id (#id token in meta grammar)
            explicit_id = parsed.get("item_id")
            if explicit_id is not None:
                g["note"]["id"] = explicit_id

            # Explicit anchor drain event
            anchor = parsed.get("anchor")
            if anchor:
                _drain_to_anchor(
                    source_file=source_file,
                    anchor=anchor,
                    line_number=g["line_num"],
                )
                g["note"] = None

            continue

        # ------------------------------------------------------------
        # Bindable symbol drain event
        # ------------------------------------------------------------
        sym, stype = meta_parse.find_bindable(line)
        if sym:
            if g["note"] is None:
                continue

            _drain_to_symbol(
                source_file=source_file,
                symbol=sym,
                symbol_type=stype,
                line_number=g["line_num"],
            )
            g["note"] = None
            continue

        # ------------------------------------------------------------
        # Ignored lines
        # ------------------------------------------------------------
        continue

    # EOF orphan handling
    if g["note"] is not None:
        _handle_orphaned_note(source_file)
        g["note"] = None
        flowctl.maybe_halt("orphaned node")


# ------------------------------------------------------------
# Note lifecycle
# ------------------------------------------------------------

def _ensure_note():
    if g["note"] is None:
        note_shape.new_note()
        g["note"]["source_file"] = str(g["path"])


def _drain_to_symbol(source_file, symbol, symbol_type, line_number):
    note = g["note"]

    note["source_file"] = source_file
    note["symbol"] = symbol
    note["symbol_type"] = symbol_type
    note["line_number"] = line_number

    _resolve_id_if_missing()

    state.db.append(note)


def _drain_to_anchor(source_file, anchor, line_number):
    """
    Drain current note into an anchor. Anchors "create if missing",
    but repeated drains to the same anchor merge into the existing anchor note.
    """
    note = g["note"]
    existing = _find_existing_anchor_note(source_file, anchor)

    if existing is None:
        # Turn this note into the anchor note, then append
        note["source_file"] = source_file
        note["symbol"] = anchor
        note["symbol_type"] = "anchor"
        note["line_number"] = line_number

        _resolve_id_if_missing()

        state.db.append(note)
        return

    # Merge this note into existing anchor note
    _merge_note_into_existing_anchor(existing, note)

    # Keep the anchor's own locator
    existing["source_file"] = source_file
    existing["symbol"] = anchor
    existing["symbol_type"] = "anchor"
    existing["line_number"] = line_number

    # If the incoming note has an explicit id, it overrides
    if note["id"]:
        existing["id"] = note["id"]
    else:
        if not existing["id"]:
            # Existing had no id (shouldn't happen if constructed correctly),
            # but keep deterministic behavior.
            existing["id"] = _derive_id(existing)


def _find_existing_anchor_note(source_file, anchor):
    i = len(state.db) - 1
    while i >= 0:
        n = state.db[i]
        if n["source_file"] == source_file and n["symbol_type"] == "anchor" and n["symbol"] == anchor:
            return n
        i -= 1
    return None


def _merge_note_into_existing_anchor(dst, src):
    """
    Merge rules (comment-spec v0.2):
      - sets/arrays: extend
      - scalars: overwrite
      - conflicts: last wins
    """
    # raw/doc always extend
    dst["raw"].extend(src["raw"])
    dst["doc"].extend(src["doc"])

    # systems/roles/threads/callers extend then normalize
    dst["systems"] = _norm_list(dst["systems"] + src["systems"], "Uc")
    dst["roles"] = _norm_list(dst["roles"] + src["roles"], "Uc")
    dst["threads"] = _norm_list(dst["threads"] + src["threads"], "Uc")
    dst["callers"] = _norm_list(dst["callers"] + src["callers"], "U")
    if src["flags"]: dst["flags"] = _merge_flags(dst["flags"], src["flags"])
    if src["assign_type"]: dst["assign_type"] = src["assign_type"]

    # custom: extend arrays per key
    for k, vals in src["custom"].items():
        if k not in dst["custom"]:
            dst["custom"][k] = []
        dst["custom"][k].extend(vals)

    # nests: (not harvested in scan currently; preserve if present)
    if src["nests"]: dst["nests"] = _norm_list(dst["nests"] + src["nests"], "U")


# ------------------------------------------------------------
# Accumulation helpers
# ------------------------------------------------------------

def _acc_raw_line():
    # store exact comment line
    g["note"]["raw"].append(g["line"])


def _acc_doc_line():
    # raw stores the full line; doc stores payload after "# doc:"
    _acc_raw_line()

    text = g["line"][6:]  # after "# doc:"
    if text.startswith(" "):
        text = text[1:]
    g["note"]["doc"].append(text)


def _acc_merge_reserved(reserved):
    note = g["note"]
    for k, vals in reserved.items():
        if k == "systems":
            note["systems"] = _norm_list(note["systems"] + vals, "Uc")
        elif k == "roles":
            note["roles"] = _norm_list(note["roles"] + vals, "Uc")
        elif k == "threads":
            note["threads"] = _norm_list(note["threads"] + vals, "Uc")
        elif k == "flags":
            note["flags"] = _norm_flags(vals)      # last wins
        elif k == "callers":
            note["callers"] = _norm_list(note["callers"] + vals, "U")
        elif k == "assign_type":
            note["assign_type"] = vals[-1] if vals else ""

def _acc_merge_custom(custom):
    note = g["note"]
    for k, vals in custom.items():
        if k not in note["custom"]:
            note["custom"][k] = []
        note["custom"][k].extend(vals)

def _is_doc_line():
    return g["line"].startswith("# doc:")


# ------------------------------------------------------------
# Identity
# ------------------------------------------------------------

def _resolve_id_if_missing():
    note = g["note"]
    if note["id"]:
        return
    note["id"] = _derive_id(note)


def _derive_id(note):
    """
    Deterministic generated id.
    (Matches note-spec intent: prefix by symbol_type, then stable components.)
    """
    prefix = _id_prefix(note["symbol_type"])
    # Use source_file + symbol + line_number for now; deterministic given unchanged source.
    return f"{prefix}{note['source_file']}:{note['symbol']}:{note['line_number']}"


def _id_prefix(symbol_type):
    if symbol_type == "module":
        return "mod:"
    if symbol_type == "function":
        return "fn:"
    if symbol_type == "class":
        return "class:"
    if symbol_type == "var":
        return "var:"
    if symbol_type == "anchor":
        return "anchor:"
    # programmer error: symbol_type must be from domain
    return "sym:"


# ------------------------------------------------------------
# Normalization / parsing
# ------------------------------------------------------------

def _norm_list(vals, flags=""):
    """
    Normalize a list of strings.

    Flags:
      U  -> unique (deduplicate, preserve first occurrence)
      c  -> lowercase

    Order is preserved.
    """
    seen = set()
    out = []

    do_unique = "U" in flags
    do_lower  = "c" in flags

    for v in vals:
        x = v.lower() if do_lower else v

        if do_unique:
            if x in seen:
                continue
            seen.add(x)

        out.append(x)

    return out


def _norm_flags(vals):
    # vals is list[str] from meta grammar, join then unique-char normalize
    s = "".join(list(vals))
    seen = set()
    out = []
    for ch in s:
        if ch in seen:
            continue
        seen.add(ch)
        out.append(ch)
    return "".join(out)


def _merge_flags(a, b):
    # merge two already-normalized flag strings; preserve order of appearance (a then b)
    seen = set()
    out = []
    for ch in a:
        if ch in seen:
            continue
        seen.add(ch)
        out.append(ch)
    for ch in b:
        if ch in seen:
            continue
        seen.add(ch)
        out.append(ch)
    return "".join(out)


def _parse_assign_type(vals):
    if not vals:
        return ""
    # scalar last-wins
    return list(vals)[-1]


def _is_int(s):
    if not s:
        return False
    for ch in s:
        if ch < "0" or ch > "9":
            return False
    return True


# ------------------------------------------------------------
# EOF orphan handling
# ------------------------------------------------------------

def _handle_orphaned_note(source_file):
    events.append_event("orphaned-node")


