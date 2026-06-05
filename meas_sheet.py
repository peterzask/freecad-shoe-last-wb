import FreeCAD as App
import helper_funcs as hf
from scanf import scanf
import foot_meas_data as fmd


# Default values as inch-fraction strings (same format user types in)
_DEFAULTS_IN = {
    'foot_len':    "11 1/8",
    'joint':       "11",
    'waist':       "9 1/2",
    'instep':      "9 3/4",
    'h_instep':    "10 1/2",
    'heel':        "13",
    'heel_height': "1 1/2",
    'ankle':       "10",
}

# Maps field name → B-column cell
_CELL_MAP = {
    'foot_len':    'B3',
    'joint':       'B4',
    'waist':       'B5',
    'instep':      'B6',
    'h_instep':    'B7',
    'heel':        'B8',
    'heel_height': 'B9',
    'ankle':       'B10',
}

# Proportion checks: (min_ratio, max_ratio) relative to foot_len in mm
# Ranges are loose — catch obvious data-entry errors without false positives
_PROPORTION_CHECKS = {
    'joint':       (0.80, 1.20),
    'waist':       (0.75, 1.10),
    'instep':      (0.78, 1.15),
    'h_instep':    (0.82, 1.20),
    'heel':        (0.90, 1.30),
    'heel_height': (0.03, 0.25),
    'ankle':       (0.75, 1.20),
}


def Doc_Spreadsheet(doc_name: str, spreadsheet_name: str):
    if doc_name in App.listDocuments():
        doc = App.getDocument(doc_name)
        print(f"Found '{doc_name}'")
    else:
        print(f"'{doc_name}' not found, opening new one.")
        doc = App.newDocument(doc_name)
        doc.UndoMode = 0
    list_of_spreadsheets = doc.findObjects("Spreadsheet::Sheet")
    spreadsheet_labels = [sp.Label for sp in list_of_spreadsheets]
    if spreadsheet_name in spreadsheet_labels:
        spreadsheet = doc.getObject(spreadsheet_name)
        is_new = False
        print(f"Spreadsheet '{spreadsheet_name}' exists, using it.")
    else:
        spreadsheet = doc.addObject("Spreadsheet::Sheet", spreadsheet_name)
        is_new = True
        print(f"Spreadsheet '{spreadsheet_name}' created new.")
    return doc, spreadsheet, is_new


def _setup_headers(fms):
    fms.set("A1", "Foot Measurements")
    fms.set("B1", "Inches Text")
    fms.set("C1", "Inches Decimal")
    fms.set("D1", "mm")
    fms.set("A2", "Foot length")
    fms.set("A3",  "foot_len")
    fms.set("A4",  "joint")
    fms.set("A5",  "waist")
    fms.set("A6",  "instep")
    fms.set("A7",  "h_instep")
    fms.set("A8",  "heel")
    fms.set("A9",  "heel_height")
    fms.set("A10", "ankle")


def _populate_defaults(fms):
    """Write default inch-fraction strings to B column. Only called on a new spreadsheet."""
    for field, cell in _CELL_MAP.items():
        fms.set(cell, _DEFAULTS_IN[field])
    print("Spreadsheet populated with default measurements.")


def _parse_inch_fraction(text: str):
    """'11 1/8' or '11+1/8' → decimal inches. Returns None on parse failure."""
    text = text.strip().replace('+', ' ')
    result = scanf("%d %d/%d", text, collapseWhitespace=True)
    if result is not None:
        whole, num, den = result
        return whole + (num / den if den != 0 else 0.0)
    result = scanf("%f", text)
    return float(result[0]) if result else None


def load_foot_measurements(doc) -> fmd.foot_meas_raw:
    """Read Foot_Measurements spreadsheet → foot_meas_raw.
    Returns defaults for any missing or unparseable cell."""
    fms = doc.getObject("Foot_Measurements")
    if fms is None:
        print("load_foot_measurements: no spreadsheet found, using defaults.")
        return fmd.foot_meas_raw()

    raw = fmd.foot_meas_raw()
    for field, cell in _CELL_MAP.items():
        contents = fms.getContents(cell)
        if not contents:
            continue
        try:
            val = fms.get(cell)
            inches = _parse_inch_fraction(str(val))
            if inches is not None:
                setattr(raw, field, inches * 25.4)
            else:
                print(f"  could not parse '{val}' in {cell} ({field}), keeping default.")
        except Exception as e:
            print(f"  error reading {cell} ({field}): {e}")
    return raw


def validate_measurements(raw: fmd.foot_meas_raw) -> bool:
    """Print warnings for measurements that look out of proportion to foot_len.
    Returns True if all pass, False if any warning fired."""
    ok = True
    fl = raw.foot_len
    if fl <= 0:
        print("VALIDATION ERROR: foot_len is zero or negative.")
        return False
    for field, (lo, hi) in _PROPORTION_CHECKS.items():
        val = getattr(raw, field)
        ratio = val / fl
        if not (lo <= ratio <= hi):
            in_val = val / 25.4
            in_fl  = fl  / 25.4
            print(f"  WARNING: {field} = {in_val:.3f}\" ({val:.1f}mm) looks wrong "
                  f"— ratio to foot_len ({in_fl:.3f}\") is {ratio:.2f}, "
                  f"expected {lo:.2f}–{hi:.2f}")
            ok = False
    if ok:
        print("validate_measurements: all proportions OK.")
    return ok


# --- Script body: open/create spreadsheet, populate if new ---
doc, fms, is_new = Doc_Spreadsheet(hf.doc_name, "Foot_Measurements")
_setup_headers(fms)
if is_new or not fms.getContents(_CELL_MAP['foot_len']):
    _populate_defaults(fms)
fms.recompute()
