"""marginalia.runtime  -- loads run-time execution data"""

import json
import importlib.resources as res


EVENT_KINDS = {}


# meta: #runtime-1 callers:1
def load_runtime_execution_data():
    _load_event_kinds()

# meta: #runtime-2 callers:load_runtime_execution_data
def _load_event_kinds():
    """
    Load event_kinds.json from the marginalia package data.

    Assumes the file lives at:
        marginalia/runtime/event_kinds.json
    (i.e. package = 'marginalia.events')
    """
    
    pkg = "marginalia.runtime"
    filename = "event_kinds.json"
    
    try:
        with res.files(pkg).joinpath(filename).open("r", encoding="utf-8") as f:
            EVENT_KINDS.update(json.load(f))
    except FileNotFoundError:
        raise RuntimeError(f"Missing packaged resource: {pkg}/{name}")

