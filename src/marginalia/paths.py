# marginalia/paths.py

import pathlib

from .state import g


# ============================================================
# Path policy query
# ============================================================

def path_for(key, flags="J"):
    """
    Return a pathing.Path for the given logical artifact key.

    key:
        "summary" | "inventory_out" | "index_out"

    flags:
        "J"  -> JSON artifact (currently informational, reserved for future use)

    Uses g["args"] and g["command"] as inputs.
    """

    args = g["args"]
    cmd = g["command"]

    # ----------------------------
    # execution summary
    # ----------------------------
    if key == "summary":
        if args.summary:
            p = args.summary
        else:
            if cmd:
                p = f"{cmd}-summary.json"
            else:
                p = "summary.json"

    # ----------------------------
    # scan outputs
    # ----------------------------
    elif key == "inventory_out":
        if cmd != "scan":
            raise KeyError("inventory_out requested when command is not 'scan'")

        if getattr(args, "output", None):
            p = args.output
        else:
            p = "inventory.json"

    # ----------------------------
    # index outputs
    # ----------------------------
    elif key == "index_out":
        if cmd != "index":
            raise KeyError("index_out requested when command is not 'index'")

        if getattr(args, "output", None):
            p = args.output
        else:
            p = "index.json"

    else:
        raise KeyError(f"Unknown path key: {key}")

    # ----------------------------
    # materialize path
    # ----------------------------
    return pathlib.Path(p)
