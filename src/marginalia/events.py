"""
marginalia.events  -- structured execution events

All user-facing messages and significant processing outcomes are modeled
as events emitted from a controlled vocabulary (event_kinds.json).

event_kinds.json:
  marginalia/src/marginalia/runtime/event_kinds.json
"""

import importlib

from . import state, runtime, reflection
from .state import g
import re



# ============================================================
# TOKEN RESOLUTION
# ============================================================

TOKEN_RE = re.compile(r"""
    (\{g:([a-zA-Z_][a-zA-Z0-9_]*)\})     |  # {g:name}
    (\{args:([a-zA-Z_][a-zA-Z0-9_]*)\})  |  # {args:attr}
    (\{fn:([a-zA-Z_][a-zA-Z0-9_]*)\})    |  # {fn:name}
    (\{ctx:([a-zA-Z_][a-zA-Z0-9_]*)\})      # {ctx:key}
""", re.VERBOSE)

def _load_named_function(path):
    mod, _, name = path.rpartition(".")
    m = importlib.import_module(mod)
    return getattr(m, name)


def _resolve_tokens(s, context):
    if not s:
        return s

    out = []
    pos = 0

    for m in TOKEN_RE.finditer(s):
        start, end = m.span()

        # literal text before token
        if start > pos:
            out.append(s[pos:start])

        if m.group(2):  # g-var
            name = m.group(2)
            val = state.g.get(name)
            out.append("" if val is None else str(val))

        elif m.group(4):  # args attribute
            name = m.group(4)
            args = state.g.get("args")
            val = getattr(args, name, None) if args else None
            out.append("" if val is None else str(val))

        elif m.group(6):  # named function
            name = m.group(6)
            spec = reflection.registry["named-functions"][name]
            fn = _load_named_function(spec["fnpath"])
            try:
                out.append(str(fn()))
            except Exception as e:
                out.append(f"<error calling {name}: {e}>")

        elif m.group(8):  # ctx value
            name = m.group(8)
            val = context.get(name) if context else None
            out.append("" if val is None else str(val))
        
        pos = end

    # trailing literal text
    if pos < len(s):
        out.append(s[pos:])

    return "".join(out)


def _resolve_data(obj, context):
    """
    Walk data-template and resolve tokens in strings.
    """

    if isinstance(obj, str):
        return _resolve_tokens(obj, context)

    if isinstance(obj, list):
        return [_resolve_data(x, context) for x in obj]

    if isinstance(obj, dict):
        return {k: _resolve_data(v, context) for k, v in obj.items()}

    return obj


# ============================================================
# EVENT EMISSION
# ============================================================

# meta: #events-1 systems=events roles=submission callers=*
def append_event(kind, context=None):
    """
    Emit event of given kind using catalog definition.
    """

    if context is None:
        context = {}
    
    if kind not in runtime.EVENT_KINDS:
        raise KeyError(f"Unknown event kind: {kind}")

    spec = runtime.EVENT_KINDS[kind]

    evt = {
        "level": spec["level"],
        "kind": kind,
        "tags": list(spec["tags"]),
        "err": spec["err"],
        "msg": _resolve_tokens(spec["msg-template"], context),
        "data": _resolve_data(spec["data-template"], context),
    }

    state.events.append(evt)
    
    # ---- failure policy hook ----
    
    if evt["level"] == "error" and g["args"].fail == "halt":
        state.g["stop_requested"] = True


# ============================================================
# PROGRAM ERROR CODE CALCULATION
# ============================================================

# meta: #events-2 systems=cli,events.examination roles=calculate callers=#cli-2,#main
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
    fail_policy = args.fail

    if state.g["stop_requested"] and fail_policy == "halt":
        return 3

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

    if has_internal:
        return 5
    if has_usage:
        return 1
    if has_schema:
        return 2
    if has_io:
        return 4

    if has_error and fail_policy == "warn":
        return 0

    if has_error and fail_policy == "halt":
        return 3

    return 0


# ============================================================
# SUMMARY PRESENTATION
# ============================================================

# meta: #events-3 systems=cli,events.examination roles=output callers=#cli-4
def generate_events_presentation_lines():
    """
    Generate human-readable summary lines from recorded events.

    Returns:
        list[str]
    """

    lines_out = []

    for e in state.events:
        if e["level"] == "info":
            pfx = "[info]"
        elif e["level"] == "warning":
            pfx = "[warn]"
        elif e["level"] == "error":
            pfx = "[err]"
        else:
            pfx = "[?]"

        msg = e.get("msg") or ""
        lines = msg.splitlines()

        indent = " " * (len(pfx) + 1)

        for i, line in enumerate(lines):
            if i == 0:
                lines_out.append(f"{pfx} {line}")
            else:
                lines_out.append(f"{indent}{line}")

    return lines_out
