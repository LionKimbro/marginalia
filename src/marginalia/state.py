# marginalia/state.py

# Global canonical inventory.

# meta: modules=state,db writers=scan_command._run_scan_command readers=*
db = []

# Global control/config state.

# meta: modules=state @g_command writers=cli.main readers=*
# meta: modules=state @g_paths writers=cli.main readers=*
# meta: modules=state @g_include_globs writers=scan_command._run_scan_command readers=*
# meta: modules=state @g_exclude_dirs writers=scan_command._run_scan_command readers=*
# meta: modules=state @g_base_path writers=scan_command._run_scan_command readers=*
# meta: modules=state @g_formatting_options writers=cli.main readers=*
g = {}
