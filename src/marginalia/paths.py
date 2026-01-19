# marginalia/paths.py

from pathlib import Path

from .state import g


# ============================================================
# Path policy query
# ============================================================


def _pathobj(p, flags=""):
    if "R" in flags:  # (R)equired
        return Path(p).expanduser().resolve(strict=True)
    else:
        return Path(p).expanduser().resolve(strict=False)


def path_for(key, flags="J"):
    """
    Return a pathlib.Path for the given logical artifact key.

    key:
        "summary" | "base" | "output"

    flags:
        "J"  -> JSON artifact (currently informational, reserved for future use)

    Uses g["args"] and g["command"] as inputs.
    """

    args = g["args"]
    cmd = args.command

    if key == "base":  # (scan root)
        return _pathobj(args.path, "R")

    elif key == "output":  # (inventory or index output file)
        return _pathobj(args.output)

    if key == "summary":
        if args.summary:
            return _pathobj(args.summary)
        else:
            return _pathobj(f"{cmd}-summary.json" if cmd else "summary.json")
    
    else:
        raise ValueError(key)
