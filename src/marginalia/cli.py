# marginalia/cli.py
import sys
import argparse
import pathlib

from . import __version__
from . import discovery
from .scan_command import run_scan_command
from .indexes_command import run_indexes_command
from .state import g


# meta: modules=cli callers=cli.main
def parse():
    g["parser"] = p = argparse.ArgumentParser(prog="marginalia", add_help=True)
    p.add_argument("--version", action="store_true", help="Print Marginalia version and exit.")

    sub = p.add_subparsers(dest="command")

    # ------------------------------------------------------------
    # scan
    # ------------------------------------------------------------
    p_scan = sub.add_parser("scan", help="Scan Python source files for Marginalia meta comments.")
    p_scan.add_argument("path", help="File or directory path to scan.", type=pathlib.Path)
    p_scan.add_argument("--inventory", nargs="?", const=True, default=None, help="Emit inventory output.")
    p_scan.add_argument("--indexes", nargs="?", const=True, default=None, help="Emit indexes output.")
    p_scan.add_argument("--pretty", action="store_true", help="Pretty-print JSON output.")
    p_scan.add_argument("--compact", action="store_true", help="Minified JSON output.")
    p_scan.add_argument("--files", default=None, help="Glob pattern restricting which files are scanned.")
    p_scan.add_argument("--exclude", default=None, help="Glob pattern for excluding files or directories.")
    p_scan.add_argument("--indexes-only", nargs="*", default=None, help="Restrict emitted indexes to the specified list.")
    p_scan.add_argument("--warn", action="store_true", help="Emit warnings for malformed or unbound meta comments.")
    p_scan.add_argument("--strict", action="store_true", help="Treat warnings as errors and return non-zero exit code.")

    # ------------------------------------------------------------
    # indexes
    # ------------------------------------------------------------
    p_idx = sub.add_parser("indexes", help="Generate indexes output from an existing Marginalia inventory file.")
    p_idx.add_argument("inventory_file", help="Path to a Marginalia inventory JSON file.")
    p_idx.add_argument("--indexes", nargs="?", const=True, default=None, help="Emit indexes output.")
    p_idx.add_argument("--pretty", action="store_true", help="Pretty-print JSON output.")
    p_idx.add_argument("--compact", action="store_true", help="Minified JSON output.")
    p_idx.add_argument("--version", action="store_true", help="Print Marginalia version and exit.")
    
    g["args"] = args = p.parse_args()
    return args


# meta: modules=cli callers=pyproject.toml
def main():
    args = parse()
    
    if args.version:
        print(f"marginalia {__version__}")
        return 0

    if args.command == "scan":
        discovery.establish_include_and_exclude()
        return run_scan_command()

    elif args.command == "indexes":
        if getattr(args, "version", False):
            print(f"marginalia {__version__}")
            return 0
        return run_indexes_command()

    else:
        g["parser"].print_help()
        return 1

