# marginalia/discovery.py
import fnmatch
import os

from .paths import join


# meta: modules=scan
DEFAULT_INCLUDE = ["*.py", "*.pyw"]
# meta: modules=scan
DEFAULT_EXCLUDE_DIRS = {".git", "__pycache__", ".venv", "build", "dist"}

# meta: modules=scan callers=scan_command._run_scan_command
def iter_source_files(root_path, files_glob=None, exclude_glob=None, exclude_dirs=None):
    if exclude_dirs is None:
        exclude_dirs = set(DEFAULT_EXCLUDE_DIRS)

    if os.path.isfile(root_path):
        if _match_file(root_path, files_glob, exclude_glob):
            yield os.path.abspath(root_path)
        return

    if not os.path.isdir(root_path):
        return

    for dirpath, dirnames, filenames in os.walk(root_path):
        # prune dirs in-place
        dirnames[:] = [d for d in dirnames if d not in exclude_dirs]
        for name in filenames:
            p = join(dirpath, name)
            if _match_file(p, files_glob, exclude_glob):
                yield os.path.abspath(p)


def _match_file(p, files_glob, exclude_glob):
    name = os.path.basename(p)

    # include filter
    if files_glob:
        if not fnmatch.fnmatch(name, files_glob):
            return False
    else:
        ok = False
        for pat in DEFAULT_INCLUDE:
            if fnmatch.fnmatch(name, pat):
                ok = True
                break
        if not ok:
            return False

    # exclude filter may apply to full path or name
    if exclude_glob:
        if fnmatch.fnmatch(name, exclude_glob) or fnmatch.fnmatch(p, exclude_glob):
            return False

    return True
