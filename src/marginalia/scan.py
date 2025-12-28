# marginalia/scan.py
import io

from .errors import MetaParseError
from .meta_parse import parse_meta_line, find_bindable, should_skip_for_binding, is_meta_line
from .item_shape import make_item


# meta: modules=scan callers=scan_command._run_scan_command
def scan_file(p, source_file_display):
    items = []
    pending = None  # dict: {"raw": str, "anchor": str|None, "kv": dict}
    warnings = []

    with open(p, "r", encoding="utf-8", errors="replace") as f:
        lines = f.readlines()

    i = 0
    n = len(lines)
    while i < n:
        line = lines[i]

        if is_meta_line(line):
            raw = line.rstrip("\n")
            try:
                parsed = parse_meta_line(line)
            except MetaParseError as e:
                raise MetaParseError(f"{source_file_display}:{i+1}: {e}")

            if parsed["anchor"]:
                # binds immediately to anchor
                item = make_item(
                    parsed["anchor"],
                    "anchor",
                    source_file_display,
                    i + 1,
                    raw,
                    parsed["kv"],
                )
                items.append(item)
                pending = None
            else:
                pending = {"raw": raw, "kv": parsed["kv"], "line_number": i + 1}

            i += 1
            continue

        if pending is not None:
            if should_skip_for_binding(line):
                i += 1
                continue

            sym, stype = find_bindable(line)
            if sym:
                item = make_item(
                    sym,
                    stype,
                    source_file_display,
                    i + 1,
                    pending["raw"],
                    pending["kv"],
                )
                items.append(item)
                pending = None
                i += 1
                continue

            # Not skippable, not bindable -> pending meta is unbound.
            warnings.append(f"{source_file_display}:{pending['line_number']}: meta comment unbound (next line not bindable)")
            pending = None
            # do not consume this line; re-process it with no pending
            continue

        i += 1

    if pending is not None:
        warnings.append(f"{source_file_display}:{pending['line_number']}: meta comment unbound (end of file)")

    return items, warnings
