# marginalia/scan_command.py

"""
Scan Command Ritual Orchestrator

Responsibilities:
- Perform minimal argument validation local to scan
- Initialize scan-related global state
- Invoke discovery and scanning machines
- Invoke post-scan validation / operations
- Emit inventory artifact to default destination

Non-responsibilities (handled elsewhere):
- Output routing and formatting
- Warning / error presentation
- Strict-mode halting
- Exit code computation
"""

import os

from pathlib import Path

from .state import db, g
from .scan import scan_file
from . import events, flowctl, db_util, io_utils, paths, discovery


# meta: modules=cli,scan callers=cli.main
def run_scan_command():
    """
    Entry point for the scan ritual.
    Performs orchestration only. All policy, presentation,
    and termination behavior is delegated to outer systems.
    """

    _validate_local_scan_args()

    _initialize_scan_state()

    db[:] = []

    for p in discovery.iter_source_files():
        scan_file(p)

    _run_post_scan_operations()

    _emit_inventory()

    # no return value; flow control + exit codes handled by CLI + events


# ------------------------------------------------------------
# Internal orchestration helpers
# ------------------------------------------------------------

def _validate_local_scan_args():
    """
    Validate only argument conflicts that are specific to scan semantics.
    Broader CLI validation is assumed to happen elsewhere.
    """
    args = g["args"]

    if not os.path.exists(args.path):
        events.append_event("path-does-not-exist")
        raise flowctl.ControlledHalt("path must exist; otherwise scan ritual is impossible")

    if args.files and Path(args.path).is_file():
        events.append_event("cannot-glob-a-file")

    if args.exclude and Path(args.path).is_file():
        events.append_event("cannot-antiglob-a-file")


def _initialize_scan_state():
    """
    Prepare global state needed by the scanning machinery.
    Path resolution and routing are assumed to be handled by
    other machines prior to invocation.
    """
    discovery.establish_include_and_exclude()


def _run_post_scan_operations():
    """
    Perform validation and normalization steps that operate on db.
    Emits events rather than raising or printing directly.
    """
    db_util.check_for_duplicate_ids()


def _emit_inventory():
    """
    Always emit inventory for scan command using default routing.
    Output routing, formatting, and failure handling are external.
    """
    io_utils.write_json(paths.path_for("output"), db)
