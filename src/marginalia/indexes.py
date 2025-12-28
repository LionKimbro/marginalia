# marginalia/indexes.py

from .state import db


# meta: modules=indexing callers=scan_command._run_scan_command,indexes_command._run_indexes_command
def build_indexes(indexes_only=None):
    want = None
    if indexes_only:
        want = set(indexes_only)

    out = {}
    if want is None or "by-symbol" in want:
        out["by-symbol"] = _by_symbol()
    if want is None or "by-file" in want:
        out["by-file"] = _by_file()
    if want is None or "by-module" in want:
        out["by-module"] = _by_multi("modules")
    if want is None or "by-thread" in want:
        out["by-thread"] = _by_multi("threads")
    if want is None or "by-flag" in want:
        out["by-flag"] = _by_flags()

    return out


def _by_symbol():
    _new_buckets()
    for obj in db:
        _add(obj, "__all__")
    return _g["buckets"]["__all__"]

def _by_file():
    _new_buckets()
    for obj in db:
        _add(obj, obj["source_file"])
    return _g["buckets"]

def _by_multi(field):
    _new_buckets()
    for obj in db:
        for bucket_name in obj[field]:
            _add(obj, bucket_name)
    return _g["buckets"]

def _by_flags():
    _new_buckets()
    for obj in db:
        for ch in obj["flags"]:
            _add(obj, ch)
    return _g["buckets"]


_g = {
    "buckets": None,   # bucket_name -> { unique_key -> obj }
    "counts": None     # bucket_name -> { base_symbol -> count }
}

def _new_buckets():
    _g["buckets"] = {}
    _g["counts"] = {}

def _add(obj, bucket_name):
    buckets = _g["buckets"]
    counts = _g["counts"]
    
    bucket = buckets.setdefault(bucket_name, {})
    bucket_counts = counts.setdefault(bucket_name, {})

    base = obj["symbol"]
    n = bucket_counts.get(base, 0)
    bucket_counts[base] = n + 1

    unique = base if n == 0 else f"{base} ({n+1})"
    bucket[unique] = obj

