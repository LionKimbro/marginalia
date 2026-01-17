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
# Execution Summary Writer (ZERO ARGUMENTS)
# ============================================================

def write_summary():
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

    summary_path = paths.path_for("summary", "J")
    io_utils.write_json(summary_path, summary)

    if args.print_summary:
        for e in state.events:
            if e["level"] == "info":
                pfx = "[info]"
            elif e["level"] == "warning":
                pfx = "[warn]"
            elif e["level"] == "error":
                pfx = "[err]"
            else:
                pfx = "[?]"

            msg = e["msg"] or ""
            
            lines = msg.splitlines()
            indent = " " * (len(pfx) + 1)
            
            for (i, line) in enumerate(lines):
                if i == 0:
                    print(f"{pfx} {line}")
                else:
                    print(f"{indent}{line}")


# ============================================================
# Main Dispatcher
# ============================================================

# meta: modules=cli callers=pyproject.toml
def main():
    g["args"] = args = parse()

    if args.version and args.command is None:
        events.report_version()
    
    elif not args.command:
        events.no_command_specified()

    else:
        try:
            if args.command == "scan":
                run_scan_command()

            elif args.command == "index":
                run_index_command()

            else:
                events.unknown_command(args.command)
        
        except flowctl.ControlledHalt:
            pass
        
        except Exception:
            events.unhandled_exception()

    # ----------------------------
    # write execution summary
    # ----------------------------
    write_summary()

    # ----------------------------
    # exit policy
    # ----------------------------
    if return_code is not None:
        return return_code

    # I'm not sure this is right --
    if errors() and args.fail == "halt":
        return 3
    
    return 0

