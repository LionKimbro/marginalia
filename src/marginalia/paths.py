# marginalia/paths.py
import os


def is_dir(p):
    return os.path.isdir(p)


def is_file(p):
    return os.path.isfile(p)


def abspath(p):
    return os.path.abspath(p)


def normpath(p):
    return os.path.normpath(p)


def relpath(p, base):
    try:
        return os.path.relpath(p, base)
    except Exception:
        return p


def splitext(p):
    return os.path.splitext(p)


def dirname(p):
    return os.path.dirname(p)


def basename(p):
    return os.path.basename(p)


def join(a, b):
    return os.path.join(a, b)
