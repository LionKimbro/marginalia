
from . import state


class ControlledHalt(Exception):
    def __init__(self, reason=None):
        self.reason = reason

def maybe_halt():
    if state.g["stop_requested"]:
        raise ControlledHalt()

