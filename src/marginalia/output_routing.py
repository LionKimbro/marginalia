# marginalia/output_routing.py
import os

from .errors import UsageError

# meta: modules=output_routing callers=scan_command._run_scan_command
def decide_scan_emits(args):
    inv_specified = args.inventory is not None
    idx_specified = args.indexes is not None

    if not inv_specified and not idx_specified:
        emit_inv = True
        emit_idx = True
    else:
        emit_inv = inv_specified
        emit_idx = idx_specified

    return emit_inv, emit_idx

# meta: modules=output_routing callers=scan_command._run_scan_command
def decide_destinations(args, base_dir, emit_inv, emit_idx):
    # Each output is routed independently.
    inv_dest = None
    idx_dest = None

    if emit_inv:
        inv_dest = _route_one(args.inventory, os.path.join(base_dir, "inventory.json"))
    if emit_idx:
        idx_dest = _route_one(args.indexes, os.path.join(base_dir, "indexes.json"))

    # stdout rules: at most one output to stdout
    n_stdout = 0
    if inv_dest == "stdout":
        n_stdout += 1
    if idx_dest == "stdout":
        n_stdout += 1
    if n_stdout > 1:
        raise UsageError("At most one output may be routed to stdout per invocation.")

    return inv_dest, idx_dest


def _route_one(opt_value, default_path):
    # opt_value meanings:
    # - None: option not specified (but may still be emitted by default -> use default)
    # - True: specified with no value -> use default
    # - "stdout": stdout
    # - "<filename>": file
    if opt_value is None:
        return default_path
    if opt_value is True:
        return default_path
    if isinstance(opt_value, str) and opt_value == "stdout":
        return "stdout"
    if isinstance(opt_value, str):
        return opt_value
    return default_path
