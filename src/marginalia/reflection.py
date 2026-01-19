


registry = {
    "g-vars": {
        "cmd": {"desc": "The command that is being executed."}
    },
    "args": {
        "fail": {"desc": "Failure policy: 'halt' or 'warn'."},
        "command": {"desc": "Primary command selected from CLI."},
        "path": {"desc": "File or directory path to scan (scan cmd)"},
        "summary": {"desc": "Path of execution summary file to write"},
        "output": {"desc": "File path to write primary command output to"},
        "json": {"desc": "'pretty' or 'compact'"},
        "files": {"desc": "Glob pattern restricting which files are scanned (scan cmd)"},
        "exclude": {"desc": "Glob pattern for excluding files or directories (scan cmd)"},
        "inventory_path": {"desc": "Path to Marginalia inventory file (index cmd)"}
    },
    "named-functions": {
        "get_version": {
            "desc": "Retrieve the version of marginalia.",
            "fnpath": "marginalia.general.get_version"
        },
        "traceback": {
            "desc": "Return a traceback string for the current exception.",
            "fnpath": "traceback.format_exc"
        }
    }
}

