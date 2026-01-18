


registry = {
    "g-vars": {
        "cmd": {"desc": "The command that is being executed."}
    },
    "args": {
        "fail": {"desc": "Failure policy: 'halt' or 'warn'."},
        "command": {"desc": "Primary command selected from CLI."}
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

