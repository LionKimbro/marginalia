# marginalia/discovery.py
import fnmatch
from pathlib import Path
from .state import g

# meta: modules=scan
DEFAULT_INCLUDE = ["*.py", "*.pyw"]

# meta: modules=scan
DEFAULT_EXCLUDE_DIRS = {".git", "__pycache__", ".venv", "build", "dist"}


# meta: modules=scan callers=cli.main
def establish_include_and_exclude():
    args = g["args"]
    
    # include globs: override or default
    g["include_globs"] = set(args.files
                             if args.files
                             else DEFAULT_INCLUDE)

    # exclude dirs: override or default
    g["exclude_globs"] = set(args.exclude_globs
                             if args.exclude_globs
                             else DEFAULT_EXCLUDE_DIRS)


# meta: modules=scan callers=scan_command._run_scan_command
def iter_source_files():
    root = g["base_path"]
    yield from _iter_source_files(root)

def _iter_source_files(p: Path):
    args = g["args"]

    name = p.name

    # exclude applies to both files and directories
    if any(fnmatch.fnmatch(name, pat) for pat in g["exclude_globs"]:
        return
    
    if p.is_dir():
        for child in p.iterdir():
            yield from _iter_source_files(child)
        return

    if p.is_file():
        if any(fnmatch.fnmatch(name, pat) for pat in g["include_globs"]):
            yield p.resolve()


