# marginalia/io_utils.py
import json
import os
import shutil
import tempfile
import sys
import traceback

from . import state


# meta: modules=io callers=*
def stderr(msg=None, exc=None):
    try:
        if msg:
            sys.stderr.write(str(msg).rstrip("\n") + "\n")
        
        if exc:
            traceback.print_exception(
                type(exc),
                exc,
                exc.__traceback__,
                file=sys.stderr,
            )

    except Exception:
        # stderr must never fail
        pass


# meta: modules=io callers=*
def write_text_atomic(p, text):
    d = os.path.dirname(p)
    if d and not os.path.isdir(d):
        os.makedirs(d, exist_ok=True)

    fd, tmp = tempfile.mkstemp(prefix=".marginalia_", suffix=".tmp", dir=d if d else None)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, p)
    except Exception:
        try:
            os.unlink(tmp)
        except Exception:
            pass
        raise

# meta: modules=io callers=*
def dump_json(obj):
    pretty = state.g["args"].json == "pretty"
    if pretty:
        return json.dumps(obj, indent=2, ensure_ascii=False)
    else:
        return json.dumps(obj, separators=(",", ":"), ensure_ascii=False)

# meta: modules=io callers=*
def write_json(p, obj):
    pretty = state.g["args"].json == "pretty"
    s = dump_json(obj)
    write_text_atomic(p, s + ("\n" if pretty else ""))
