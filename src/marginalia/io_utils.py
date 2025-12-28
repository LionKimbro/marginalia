# marginalia/io_utils.py
import json
import os
import shutil
import tempfile


# meta: modules=io callers=*
def stderr(msg):
    sysmsg = msg.rstrip("\n")
    try:
        import sys
        sys.stderr.write(sysmsg + "\n")
    except Exception:
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
def dump_json(obj, pretty=False, compact=False):
    if pretty and compact:
        raise ValueError("cannot combine pretty and compact")

    if pretty:
        return json.dumps(obj, indent=2, ensure_ascii=False)

    # compact is the default behavior in the contract (and in practice)
    return json.dumps(obj, separators=(",", ":"), ensure_ascii=False)

# meta: modules=io callers=*
def write_json(p, obj, pretty=False, compact=False):
    s = dump_json(obj, pretty=pretty, compact=compact)
    write_text_atomic(p, s + ("\n" if pretty else ""))
