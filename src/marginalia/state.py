# marginalia/state.py

# Global canonical inventory.

# meta: #db modules=state,db writers=scan_command._run_scan_command readers=*
db = []

# Global control/config state.

# meta: #g_parser modules=state @g_parser writers=cli.main readers=cli.main
# meta: #g_args modules=state @g_args writers=cli.main readers=*

# meta: #g_command modules=state @g_command writers=cli.main readers=*
# meta: #g_paths modules=state @g_paths writers=cli.main readers=*

# meta: #g_path modules=state @g_path writers=file_nav.start_reading readers=*
# meta: #g_file modules=state @g_file writers=file_nav.start_reading readers=*
# meta: #g_line_num modules=state @g_line_num writers=file_nav.start_reading,file_nav.read_line readers=*
# meta: #g_line modules=state @g_line writers=file_nav.start_reading,file_nav.read_line readers=*
# meta: #g_finished_reading_file modules=state @g_finished_reading_file writers=file_nav.start_reading,file_nav.read_line readers=*

# meta: #g_item modules=state @g_item writers=scan.scan_file,item_shape.new_item readers=*
# meta: #g_include_globs modules=state @g_include_globs writers=scan_command._run_scan_command readers=*
# meta: #g_exclude_dirs modules=state @g_exclude_dirs writers=scan_command._run_scan_command readers=*
# meta: #g_base_path modules=state @g_base_path writers=scan_command._run_scan_command readers=*
# meta: #g_formatting_options modules=state @g_formatting_options writers=cli.main readers=*
g = {
    "parser": None,
    "args": None,

    "command": None,
    "paths": None,

    "path": None,
    "file": None,
    "line_num": None,
    "line": None,
    "finished_reading_file": None,
    
    "item": None,
    "include_globs": None,
    "exclude_dirs": None,
    "base_path": None,
    "formatting_options": None
}


# meta: #warnings modules=state writers=scan.scan_file readers=*
warnings = []

