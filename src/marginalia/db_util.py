"""marginalia.db_util  -- utilities involved with db maintenance"""

from . import events

from .state import db


def check_for_duplicate_ids():
    seen = {}
    for i, note in enumerate(db):
        note_id = note["id"]
        if note_id in seen:
            first_i = seen[note_id]
            events.append_event("duplicate-note-id-detected",
                                {"note_id": note_id,
                                 "first_i": first_i,
                                 "i": i})
        else:
            seen[note_id] = i

