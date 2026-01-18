# marginalia/cli.py
import sys
import argparse
import pathlib
import time
import traceback

from . import __version__
from .scan_command import run_scan_command
from .index_command import run_index_command
from .state import g
from . import io_utils
from . import paths
from . import events
from . import flowctl
from . import runtime


# ============================================================
# CLI Parsing
# ============================================================

# meta: modules=cli callers=cli.main
def parse():
    p = argparse.ArgumentParser(
        prog="marginalia",
        description="Static analysis tool for extracting Marginalia meta comments from Python source code."
    )

    # ----------------------------
    # universal options
    # ----------------------------
    p.add_argument("--version", action="store_true", help="Print Marginalia version and exit.")
    p.add_argument("--summary", default=None, help="Path of execution summary file to write.")
    p.add_argument("--print-summary", action="store_true",
                   help="Print execution summary JSON to stdout after completion.")
    p_scan.add_argument("--output", default=None, help="File to write output to.")
    p.add_argument("--fail", choices=["warn", "halt"], default="halt",
                   help="Failure handling policy when errors are encountered.")
    p.add_argument("--json", choices=["pretty", "compact"], default="pretty",
                   help="JSON formatting style for output artifacts.")

    sub = p.add_subparsers(dest="command")

    # ----------------------------
    # scan
    # ----------------------------
    p_scan = sub.add_parser("scan", help="Scan Python source files and generate inventory artifact.")
    p_scan.add_argument("path", nargs="?", default=".", help="File or directory path to scan.")
    p_scan.add_argument("--files", default=None, help="Glob pattern restricting which files are scanned.")
    p_scan.add_argument("--exclude", default=None, help="Glob pattern for excluding files or directories.")

    # ----------------------------
    # index
    # ----------------------------
    p_idx = sub.add_parser("index", help="Generate indexes from an existing inventory artifact.")
    p_idx.add_argument("inventory_path", nargs="?", default=None,
                       help="Path to Marginalia inventory JSON file.")

    return p.parse_args()


# ============================================================
# Execution Summary
# ============================================================

def prepare_summary_dict():
    """
    Construct execution summary object from global state and events.

    Returns:
        dict
    """
    args = g["args"]
    errcode = events.calculate_errcode()

    summary = {
        "version": "marginalia.execution-summary.v0.2",
        "invocation": {
            "command-line": " ".join(sys.argv),
            "execution-mode": args.command,
            "time-of-execution": time.time(),
        },
        "result": "success" if errcode == 0 else "failure",
        "errcode": errcode,
        "events": state.events,
    }

    return summary


def write_summary_output_file():
    """
    Write execution summary JSON to standard summary path.
    """
    summary = prepare_summary_dict()
    summary_path = paths.path_for("summary", "J")
    io_utils.write_json(summary_path, summary)


def print_events_output_lines():
    """
    Print human-readable summary presentation lines to stdout.
    """
    for line in events.generate_events_presentation_lines():
        print(line)


# ============================================================
# Main Dispatcher
# ============================================================

# meta: modules=cli callers=pyproject.toml
def main():
    runtime.load_runtime_execution_data()
    
    g["args"] = args = parse()

    if args.version and args.command is None:
        events.append_event("report-version")
    
    elif not args.command:
        events.append_event("no-command-specified")

    else:
        try:
            if args.command == "scan":
                run_scan_command()

            elif args.command == "index":
                run_index_command()

            else:
                events.append_event("unknown-command")
        
        except flowctl.ControlledHalt:
            pass
        
        except Exception:
            events.append_event("unhandled-exception")
    
    # ----------------------------
    # write execution summary
    # ----------------------------
    events.write_summary_output_file()

    if args.print_summary:
        print_events_output_lines():


    # ----------------------------
    # exit policy
    # ----------------------------
    return events.calculate_errcode()

