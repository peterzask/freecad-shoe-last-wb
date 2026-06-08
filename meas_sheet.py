import FreeCAD as App
import helper_funcs as hf
import foot_meas_data as fmd
from math import gcd


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
    'toe_space':   "5/8",
}

# Maps field name → column cells (B=text, C=decimal inches, D=mm)
_CELL_MAP = {
    'foot_len':    'B3',
    'joint':       'B4',
    'waist':       'B5',
    'instep':      'B6',
    'h_instep':    'B7',
    'heel':        'B8',
    'heel_height': 'B9',
    'ankle':       'B10',
    'toe_space':   'B11',
}
_CELL_MAP_C = {k: 'C' + v[1:] for k, v in _CELL_MAP.items()}
_CELL_MAP_D = {k: 'D' + v[1:] for k, v in _CELL_MAP.items()}

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


def Doc_Spreadsheet(doc_name, spreadsheet_name: str):
    if doc_name is None:
        doc = App.ActiveDocument
        if doc is None:
            raise RuntimeError("Doc_Spreadsheet: no active FreeCAD document.")
    elif doc_name in App.listDocuments():
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


_TOE_SPACE_MM = 15.0  # standard toe allowance (Koleff constant, matches insole_len_c.BD)


def _setup_headers(fms):
    fms.set("A1", "Foot Measurements")
    fms.set("B1", "Inches Text")
    fms.set("C1", "Inches Decimal")
    fms.set("D1", "mm")
    fms.set("E1", "US Size")
    fms.set("A2", "Foot length")
    fms.set("A3",  "foot_len")
    fms.set("A4",  "joint")
    fms.set("A5",  "waist")
    fms.set("A6",  "instep")
    fms.set("A7",  "h_instep")
    fms.set("A8",  "heel")
    fms.set("A9",  "heel_height")
    fms.set("A10", "ankle")
    fms.set("A11", "toe_space")


def _populate_defaults(fms):
    """Write defaults to any empty B cells and immediately derive C and D."""
    for field, cell_b in _CELL_MAP.items():
        if not fms.getContents(cell_b):
            text = _DEFAULTS_IN[field]
            fms.set(cell_b, text)
            inches = _parse_inch_fraction(text)
            if inches is not None:
                fms.set(_CELL_MAP_C[field], f"{inches:.4f}")
                fms.set(_CELL_MAP_D[field], f"{inches * 25.4:.2f}")
            print(f"  default set: {cell_b} = {text}")


def _parse_inch_fraction(text: str):
    """Parse inch text → decimal inches. Handles '11 1/8', '11+1/8', '5/8', '11.125', '11'.
    FreeCAD getContents() prefixes formula cells with '=' and text cells with \"'\" — strip both."""
    text = text.strip().replace('+', ' ')
    if text.startswith("'"):
        text = text[1:]
    elif text.startswith('='):
        text = text[1:].replace(' ', '')  # '=5 / 8' → '5/8'
    try:
        parts = text.split()
        if len(parts) == 2 and '/' in parts[1]:
            whole = int(parts[0])
            num, den = parts[1].split('/', 1)
            return whole + int(num) / int(den)
        elif len(parts) == 1:
            if '/' in parts[0]:
                num, den = parts[0].split('/', 1)
                return int(num) / int(den)
            else:
                return float(parts[0])
    except (ValueError, ZeroDivisionError):
        pass
    return None


def _format_inch_fraction(inches: float) -> str:
    """Decimal inches → 'whole N/D' text rounded to nearest 1/8\"."""
    whole = int(inches)
    eighths = round((inches - whole) * 8)
    if eighths == 8:
        whole += 1
        eighths = 0
    if eighths == 0:
        return str(whole)
    g = gcd(eighths, 8)
    return f"{whole} {eighths // g}/{8 // g}"


def _sync_row(fms, cell_b, cell_c, cell_d):
    """Derive the two empty cells from the one filled cell.
    If zero or two-or-more cells are filled, do nothing — user must clear first."""
    b = fms.getContents(cell_b)
    c = fms.getContents(cell_c)
    d = fms.getContents(cell_d)
    filled = sum(1 for x in [b, c, d] if x)
    if filled != 1:
        return
    if b:
        inches = _parse_inch_fraction(b)
        if inches is None:
            return
        fms.set(cell_c, f"{inches:.4f}")
        fms.set(cell_d, f"{inches * 25.4:.2f}")
    elif c:
        try:
            inches = float(c)
        except (TypeError, ValueError):
            return
        fms.set(cell_b, _format_inch_fraction(inches))
        fms.set(cell_d, f"{inches * 25.4:.2f}")
    else:
        try:
            mm = float(d)
        except (TypeError, ValueError):
            return
        inches = mm / 25.4
        fms.set(cell_b, _format_inch_fraction(inches))
        fms.set(cell_c, f"{inches:.4f}")


def _sync_columns(fms):
    """Sync B/C/D columns for all measurement rows."""
    for field in _CELL_MAP:
        _sync_row(fms, _CELL_MAP[field], _CELL_MAP_C[field], _CELL_MAP_D[field])


def _sync_size_column(fms):
    """Compute US shoe size from foot_len and write to E3.
    Formula: last_length = foot_len + toe_space; size = (last_inches - 8) * 3"""
    d3 = fms.getContents('D3')
    if d3:
        try:
            foot_len_mm = float(d3)
        except (TypeError, ValueError):
            foot_len_mm = None
    else:
        b3 = fms.getContents('B3')
        if not b3:
            return
        inches = _parse_inch_fraction(b3)
        foot_len_mm = inches * 25.4 if inches is not None else None

    if not foot_len_mm or foot_len_mm <= 0:
        return
    d11 = fms.getContents('D11')
    try:
        toe_space_mm = float(d11) if d11 else _TOE_SPACE_MM
    except (TypeError, ValueError):
        toe_space_mm = _TOE_SPACE_MM
    last_inches = (foot_len_mm + toe_space_mm) / 25.4
    size = (last_inches - 8.0) * 3.0
    fms.set('E3', f"{size:.1f}")


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


# --- Script body: open/create spreadsheet, populate if new, sync columns ---
doc, fms, is_new = Doc_Spreadsheet(None, "Foot_Measurements")
_setup_headers(fms)
_populate_defaults(fms)
fms.recompute()
_sync_columns(fms)
_sync_size_column(fms)
fms.recompute()
