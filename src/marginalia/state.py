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

# ============================================================
# Assembly workbench (per scan_file invocation)
# ============================================================


asm = {
    # meta: modules=scan @asm_source_file writers=scan.scan_file readers=scan.scan_file,item_shape.make_item
    # Contextual source file identifier (display name / path).
    "source_file": None,

    # meta: modules=scan @asm_raw writers=scan.scan_file readers=scan.scan_file,item_shape.make_item
    # Raw "# meta: ..." line text (exact, unparsed).
    "raw": None,

    # meta: modules=scan @asm_meta_kv writers=scan.scan_file readers=scan.scan_file,item_shape.make_item
    # Parsed key/value pairs from the meta line.
    "meta_kv": None,

    # meta: modules=scan @asm_explicit_item_id writers=scan.scan_file readers=scan.scan_file,item_shape.make_item
    # Explicit item id token (e.g. "#foo"), if provided in meta line.
    "explicit_item_id": None,

    # meta: modules=scan @asm_anchor writers=scan.scan_file readers=scan.scan_file,item_shape.make_item
    # Anchor symbol from meta line (e.g. "@symbol"), if present.
    "anchor": None,

    # meta: modules=scan @asm_meta_line_number writers=scan.scan_file readers=scan.scan_file,item_shape.make_item
    # Line number where the meta line occurred.
    "meta_line_number": None,

    # meta: modules=scan @asm_symbol writers=scan.scan_file readers=scan.scan_file,item_shape.make_item
    # Bound symbol name (from anchor or find_bindable).
    "symbol": None,

    # meta: modules=scan @asm_symbol_type writers=scan.scan_file readers=scan.scan_file,item_shape.make_item
    # Symbol type: "function", "class", "data", or "anchor".
    "symbol_type": None,

    # meta: modules=scan @asm_line_number writers=scan.scan_file readers=scan.scan_file,item_shape.make_item
    # Line number where the symbol binding occurred.
    "line_number": None,

    # meta: modules=scan @asm_item_id writers=scan.scan_file readers=scan.scan_file,item_shape.make_item
    # Resolved item id (explicit or derived as "filename.symbol").
    "item_id": None
}


# meta: modules=scan writers=scan.scan_file callers=scan.scan_file
def asm_reset():
    """
    Reset assembly state between items.

    Preserves contextual fields that are constant for the duration
    of a scan_file invocation (e.g. source_file).
    """
    asm["raw"] = None
    asm["meta_kv"] = None
    asm["explicit_item_id"] = None
    asm["anchor"] = None
    asm["meta_line_number"] = None
    asm["symbol"] = None
    asm["symbol_type"] = None
    asm["line_number"] = None
    asm["item_id"] = None

