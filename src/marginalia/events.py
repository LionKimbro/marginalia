"""marginalia.events  -- information while processing

All significant events for review go here.
All messages to the user are modeled as events.
"""

import traceback

from . import state
from . import __version__


# Events in (state.events) have the following form:
# {"level": "warning" | "error" | "info",
#  "kind": "programmatic identity of event; ex: too-many-arguments",
#  "tags": [] | ["success"] | ["fail"] | [...]  -- for future expansion
#  "err": None | "usage" | "schema" | "io"
#  "msg": "<human readable text string>",
#  "data": {...}}
#
# (data contains raw data associated with the message; it should be JSON serializable)

g = {
    "evt": None  # event under construction
}


########################################################################
# EVENT CONSTRUCTION
########################################################################

def _blank_evt():
    g["evt"] = {
        "level": None,
        "kind": None,
        "tags": [],
        "err": None,
        "msg": None,
        "data": {}
    }


def _log_evt():
    e = g["evt"]
    assert e["level"] is not None
    assert e["kind"] is not None
    assert e["msg"] is not None
    state.events.append(e)
    g["evt"] = None


def _start_evt(kind, flags):
    _blank_evt()
    e = g["evt"]

    if "i" in flags:
        e["level"] = "info"
    elif "w" in flags:
        e["level"] = "warning"
    elif "e" in flags:
        e["level"] = "error"
        if state.g["args"].fail == "halt":
            state.g["stop_requested"] = True
    else:
        assert False, "event flags must include one of: i, w, e"

    e["kind"] = kind

    if "S" in flags:
        e["tags"].append("success")
    elif "F" in flags:
        e["tags"].append("fail")


def _set_err(s):
    assert s in ("usage", "schema", "io", "internal")
    g["evt"]["err"] = s


def _set_msg(s):
    g["evt"]["msg"] = s


def _set_key(k, v):
    g["evt"]["data"][k] = v


########################################################################
# PROGRAM ERROR CODE CALCULATION
########################################################################

# in marginalia/events.py
from . import state
from .state import g


def calculate_errcode():
    """
    Compute exit code from events + policy.

    Exit codes (contract):
      0 = Success (no errors, or --fail=warn)
      1 = Usage or argument error
      2 = Parse or schema validation error
      3 = Failure policy halt condition triggered (early out)
      4 = Filesystem or IO error
      5 = Internal error (crash / unhandled exception)
    """

    args = g["args"]
    fail_policy = args.fail  # expects "halt" or "warn"

    # If we halted due to policy, that's a distinct outcome.
    # (This should be set when an error-level event is emitted under fail=halt.)
    if state.g["stop_requested"] and fail_policy == "halt":
        return 3

    # Scan events for error classes.
    has_error = False
    has_usage = False
    has_schema = False
    has_io = False
    has_internal = False

    for e in state.events:
        if e["level"] != "error":
            continue

        has_error = True
        if e["err"] == "usage":
            has_usage = True
        elif e["err"] == "schema":
            has_schema = True
        elif e["err"] == "io":
            has_io = True
        elif e["err"] == "internal":
            has_internal = True

    # Highest priority: internal errors
    if has_internal:
        return 5

    # Next: explicit categories
    if has_usage:
        return 1
    if has_schema:
        return 2
    if has_io:
        return 4

    # If there were errors but policy is warn, success by contract.
    if has_error and fail_policy == "warn":
        return 0

    # If there were errors and policy is halt, but stop_requested wasn't set
    # (e.g., programming mistake or errors recorded late), treat as policy halt.
    if has_error and fail_policy == "halt":
        return 3

    return 0


########################################################################
# EVENTS
########################################################################
    
def report_version():
    _start_evt("report-version", "i")
    _set_msg(f"marginalia {__version__}")
    _set_key("version", __version__)
    _log_evt()

def no_command_specified():
    _start_evt("no-command-specified", "e")
    _set_err("usage")
    _set_msg("No command specified.")
    _log_evt()

def unknown_command(cmd):
    _start_evt("unknown-command", "e")
    _set_err("usage")
    _set_msg(f"Unknown command: {cmd}")
    _set_key("cmd", cmd)
    _log_evt()

def unhandled_exception():
    traceback_str = traceback.format_exc()
    _start_evt("unhandled-exception", "e")
    _set_err("internal")
    _set_msg("fatal: unhandled exception (see traceback)\n" + traceback_str)
    _set_key("traceback", traceback_str)
    _log_evt()
