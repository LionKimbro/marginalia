# marginalia/file_nav.py
from . import state
from .state import g


# ============================================================
# File navigation helpers (scan-time cursor state)
# ============================================================

# meta: modules=scan callers=scan.scan_file
def start_reading(p):
    """
    Initialize global scan cursor state for a file.
    """
    g["path"] = p
    g["file"] = open(p, "r", encoding="utf-8", errors="replace")
    g["line_num"] = 0
    g["line"] = None
    g["finished_reading_file"] = False

# meta: modules=scan callers=scan.scan_file
def read_line():
    """
    Advance the file cursor by one line.

    Updates:
      - g["line"]     : current line (string, no trailing newline)
      - g["line_num"] : 1-based line number
      - g["finished_reading_file"] : True on EOF

    Returns:
      True if a line was read, False if EOF was reached.
    """
    if g["finished_reading_file"]:
        return False
    
    line = g["file"].readline()
    if not line:
        g["line"] = None
        g["line_num"] = None
        g["finished_reading_file"] = True
        return False

    g["line_num"] += 1
    g["line"] = line.rstrip("\n")
    return True

