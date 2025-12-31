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
    if args.files:
        g["include_globs"] = {args.files}
    else:
        g["include_globs"] = set(DEFAULT_INCLUDE)

    # exclude dirs: override or default
    if getattr(args, "exclude_dirs", None):
        g["exclude_dirs"] = set(args.exclude_dirs)
    else:
        g["exclude_dirs"] = set(DEFAULT_EXCLUDE_DIRS)


# meta: modules=scan callers=scan_command._run_scan_command
def iter_source_files():
    root = Path(g["args"].path)
    yield from _iter_source_files(root)

def _iter_source_files(p: Path):
    if p.is_dir():
        if p.name in g["exclude_dirs"]:
            return
        for child in p.iterdir():
            yield from _iter_source_files(child)
        return

    if p.is_file():
        if any(p.match(glob) for glob in g["include_globs"]):
            yield p.resolve()


