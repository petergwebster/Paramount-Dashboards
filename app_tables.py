import streamlit as st

def require_tables():
    """
    Enforces that the workbook tables were loaded on the Data page and are
    available in session state. Stops the page with a friendly message if not.
    """
    tables = st.session_state.get("sheets_raw")
    if tables is None or not isinstance(tables, dict) or len(tables) == 0:
        st.warning("No data loaded yet. Go to the Data page and click Load and preview selected tabs.")
        st.stop()
    return tables

def _norm_name(name_in):
    """
    Normalizes a sheet name so small differences (spaces, punctuation, casing)
    don't matter. Keeps only alphanumeric characters.
    """
    return "".join([c.lower() for c in str(name_in).strip() if c.isalnum()])

def list_tables(tables=None):
    """
    Returns a sorted list of sheet names currently loaded in memory.

    If `tables` is not passed, it will pull from session via require_tables(),
    so it never reloads from disk.
    """
    if tables is None:
        tables = require_tables()
    return sorted(list(tables.keys()), key=lambda x: str(x).lower())

def tables_debug_map(tables=None):
    """
    Debug helper: returns a list of dicts showing actual sheet name and its
    normalized form, useful for diagnosing matching issues.
    """
    if tables is None:
        tables = require_tables()

    rows = []
    for k in tables.keys():
        rows.append({"sheet_name": k, "normalized": _norm_name(k)})
    rows = sorted(rows, key=lambda r: str(r["sheet_name"]).lower())
    return rows

def get_table(tables, desired_name):
    """
    Retrieves a dataframe from `tables` using robust matching:
    - direct match
    - normalized exact match
    - normalized contains match
    - synonym candidates (for your priority sheets)
    Returns (df, actual_sheet_name) or (None, None) if not found.
    """
    synonyms = {
        "written produced by week": [
            "written produced by week",
            "written produced week",
            "written produced weekly",
            "written produced by wk",
            "written produced",
            "written v produced by week",
        ],
        "written produced invoiced": [
            "written produced invoiced",
            "written produced & invoiced",
            "written produced and invoiced",
            "written produced invoice",
            "written produced invoicing",
        ],
        "ytd plan v actual": [
            "ytd plan v actual",
            "ytd plan vs actual",
            "ytd plan v. actual",
            "plan v actual ytd",
            "plan vs actual ytd",
            "ytd plan actual",
        ],
        "ytd v ly": [
            "ytd v ly",
            "ytd vs ly",
            "ytd v. ly",
            "ytd vs last year",
            "ytd v last year",
            "ytd vs last yr",
        ],
        "color yds": [
            "color yds",
            "color yards",
            "color yds.",
            "color yards",
            "color yards report",
            "color yards by",
            "color",
        ],
        "wip": [
            "wip",
            "work in process",
            "work in progress",
        ],
        "yds wasted": [
            "yds wasted",
            "yards wasted",
            "waste yds",
            "wasted yards",
            "yds waste",
            "yards waste",
        ],
    }

    desired_key = str(desired_name).strip().lower()
    candidates = synonyms.get(desired_key, [desired_name])

    for cand in candidates:
        if cand in tables:
            return tables[cand], cand

    for cand in candidates:
        cand_norm = _norm_name(cand)

        for k in tables.keys():
            if _norm_name(k) == cand_norm:
                return tables[k], k

        for k in tables.keys():
            if cand_norm in _norm_name(k):
                return tables[k], k

    if desired_name in tables:
        return tables[desired_name], desired_name

    desired_norm = _norm_name(desired_name)

    for k in tables.keys():
        if _norm_name(k) == desired_norm:
            return tables[k], k

    for k in tables.keys():
        if desired_norm in _norm_name(k):
            return tables[k], k

    return None, None
