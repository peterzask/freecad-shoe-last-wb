"""Sandbox: interpolated surface + degree-3 surface, vs. current degree-2.

Experiments:
  A) BSplineSurface.interpolate(rows)  — passes through every control point
  B) degree=3 buildFromPolesMultsKnots — reduces hull shrinkage vs degree=2
  C) degree=2 with triple-multiplicity at C1 knot in v — forces surface through
     the C1 ring without a full interpolation

Run from FreeCAD macro menu. Shows each variant as a named Part::Feature so
they can be toggled visible/invisible for comparison.
"""
import importlib
import inspect
import FreeCAD as App
import FreeCADGui
import Part
import helper_funcs as hf
import last_insole
import last_profile
import xs_base
import xs_heel_near
import xs_0, xs_1, xs_2, xs_3, xs_4, xs_5, xs_6, xs_7, xs_8, xs_9
import control_curves

importlib.reload(hf)
importlib.reload(last_insole)
importlib.reload(last_profile)
importlib.reload(control_curves)
importlib.reload(xs_base)
for _m in [xs_0, xs_1, xs_2, xs_3, xs_4, xs_5, xs_6, xs_7, xs_8, xs_9]:
    importlib.reload(_m)
importlib.reload(xs_heel_near)

print(f"+++++++++++++++Line({inspect.currentframe().f_lineno}) File:({__file__})+++++++++++++++++++")

# ---------------------------------------------------------------------------
# Build rows — identical to uv_0.py
# ---------------------------------------------------------------------------
xs_list = [
    (xs_0.xs_0,  xs_base.xs_0_placement),
    (xs_1.xs_1,  xs_base.xs_1_placement),
    (xs_2.xs_2,  xs_base.xs_2_placement),
    (xs_3.xs_3,  xs_base.xs_3_placement),
    (xs_4.xs_4,  xs_base.xs_4_placement),
    (xs_5.xs_5,  xs_base.xs_5_placement),
    (xs_6.xs_6,  xs_base.xs_6_placement),
    (xs_7.xs_7,  xs_base.xs_7_placement),
    (xs_8.xs_8,  xs_base.xs_8_placement),
    (xs_9.xs_9,  xs_base.xs_9_placement),
]

crisp_sole = True
rows = [list(xs_base.get_heel_end_row(crisp_sole=crisp_sole))]
pl_hn = xs_base.xs_heel_near_placement * hf.yz_xy_place
rows.append(xs_heel_near.xs_heel_near.row_world(pl_hn, crisp_sole=crisp_sole))
for xs, placement in xs_list:
    pl = placement * hf.yz_xy_place
    rows.append([pl.multVec(pv) for pv in xs.ctrl.control_points(crisp_sole=crisp_sole)])
rows.append(list(xs_base.xs_toe_end_row))

u_count = len(rows)
v_count = len(rows[0])
print(f"u_count={u_count}  v_count={v_count}")

# ---------------------------------------------------------------------------
# Shared knot helpers
# ---------------------------------------------------------------------------
def _hartley_judd_knots(params, degree):
    n = len(params)
    interior = [sum(params[j:j+degree]) / degree for j in range(1, n - degree)]
    knots = [0.0] + interior + [1.0]
    mults  = [degree + 1] + [1] * len(interior) + [degree + 1]
    return knots, mults

def _chord_params_u(rows, C_idx):
    raw = [0.0]
    for u in range(1, len(rows)):
        raw.append(raw[-1] + (rows[u][C_idx] - rows[u-1][C_idx]).Length)
    total = raw[-1]
    return [k / total for k in raw]

def _chord_params_v(ring):
    raw = [0.0]
    for v in range(1, len(ring)):
        raw.append(raw[-1] + (ring[v] - ring[v-1]).Length)
    total = raw[-1]
    return [k / total for k in raw]

C_idx   = v_count // 2 + 1        # C point index in v (same as uv_0.py)
ref_row = 5                        # xs_3 chord-length reference row

uks_raw = _chord_params_u(rows, C_idx)
vks_raw = _chord_params_v(rows[ref_row])

# ---------------------------------------------------------------------------
# Helper: show a shape as a named object
# ---------------------------------------------------------------------------
def _show(shape, name):
    doc = App.ActiveDocument
    if doc.getObject(name):
        doc.removeObject(name)
    obj = doc.addObject("Part::Feature", name)
    obj.Shape = shape
    print(f"  {name}: done")

def _dedupe_v_columns(rows, ref_row_idx, tol=1e-9, open_ring=False, drop_indices=()):
    # crisp_sole=True doubles H1 back-to-back (zero chord length), which
    # global chord-length interpolate() rejects ("VKnots interval values
    # too close"). Drop the duplicate column from every row before A only —
    # B/C build from poles directly and tolerate a duplicate pole fine.
    ref = rows[ref_row_idx]
    v_indices = [v for v in range(len(ref)) if v not in drop_indices]
    keep = [v_indices[0]]
    for v in v_indices[1:]:
        if (ref[v] - ref[keep[-1]]).Length > tol:
            keep.append(v)
    if open_ring and (ref[keep[-1]] - ref[keep[0]]).Length <= tol:
        # H2 closes the ring back onto v=0. interpolate() has no periodic
        # option (checked BSplineSurfacePyImp.cpp — plain non-periodic
        # GeomAPI_PointsToBSplineSurface::Interpolate), so it independently
        # estimates end tangents at v=0 and v=1 that don't agree at this
        # coincident point — that mismatch is the H2-seam blowup. Drop the
        # closing duplicate and leave v as a genuinely open strip.
        keep = keep[:-1]
    return [[row[v] for v in keep] for row in rows]

# ---------------------------------------------------------------------------
# Experiment A: BSplineSurface.interpolate
# ---------------------------------------------------------------------------
print("\n--- Experiment A: BSplineSurface.interpolate ---")
rows_A = _dedupe_v_columns(rows, ref_row, open_ring=True)
try:
    nurb_A = Part.BSplineSurface()
    nurb_A.interpolate(rows_A)
    _show(nurb_A.toShape(), "Interp_A_interpolate")
except Exception as e:
    print(f"  interpolate() failed: {e}")

# ---------------------------------------------------------------------------
# Experiment A2: same as A, but also drop H3 (raw ring index 1) — opens up
# the bottom of the last too, to test whether the H2 spike is really coming
# from the short H2-H3 crease rather than just the closing-loop mismatch.
# ---------------------------------------------------------------------------
print("\n--- Experiment A2: interpolate, H3 dropped (open bottom) ---")
rows_A2 = _dedupe_v_columns(rows, ref_row, open_ring=True, drop_indices={1})
try:
    nurb_A2 = Part.BSplineSurface()
    nurb_A2.interpolate(rows_A2)
    _show(nurb_A2.toShape(), "Interp_A2_open_bottom")
except Exception as e:
    print(f"  interpolate() (open bottom) failed: {e}")

# ---------------------------------------------------------------------------
# Experiment B: degree=3
# ---------------------------------------------------------------------------
print("\n--- Experiment B: degree=3 buildFromPolesMultsKnots ---")
deg3 = 3
uks3, u_mults3 = _hartley_judd_knots(uks_raw, deg3)
vks3, v_mults3 = _hartley_judd_knots(vks_raw, deg3)
try:
    nurb_B = Part.BSplineSurface()
    nurb_B.buildFromPolesMultsKnots(
        rows, u_mults3, v_mults3, uks3, vks3,
        uperiodic=False, vperiodic=False,
        udegree=deg3, vdegree=deg3)
    _show(nurb_B.toShape(), "Interp_B_degree3")
except Exception as e:
    print(f"  degree-3 failed: {e}")

# ---------------------------------------------------------------------------
# Experiment C: degree=2 + multiplicity=2 (=degree) at the C1 knot in v
# (forces the C1 ring onto the surface itself)
# C1 is at v-index 5: H2 H3 H1 H1c T1 C1 C C2 T2 H2
# ---------------------------------------------------------------------------
print("\n--- Experiment C: degree=2, multiplicity=degree at C1 v-knot ---")
C1_v_idx = 5   # index in the 10-point crisp_sole ring

vks_raw_c = _chord_params_v(rows[ref_row])
_vp_C1 = vks_raw_c[C1_v_idx]

# Build knot vector: Hartley-Judd base, then insert a knot at C1's own
# chord parameter (previously this searched vks2 for the nearest averaged
# interior knot, which is always the midpoint to a neighbor, never _vp_C1
# itself — see 2026-07-18 conversation).
vks2, v_mults2 = _hartley_judd_knots(vks_raw_c, 2)
uks2, u_mults2 = _hartley_judd_knots(uks_raw, 2)

try:
    nurb_C = Part.BSplineSurface()
    nurb_C.buildFromPolesMultsKnots(
        rows, u_mults2, v_mults2, uks2, vks2,
        uperiodic=False, vperiodic=False,
        udegree=2, vdegree=2)
    # Multiplicity == degree at an interior knot puts one pole exactly on
    # the curve there. insertVKnot is shape-preserving though — it only
    # exposes that pole, it doesn't move the surface to rows[*][C1_v_idx].
    nurb_C.insertVKnot(_vp_C1, 2, 1e-7)
    print(f"  C1 v-knot inserted at param={_vp_C1:.4f}")
    _show(nurb_C.toShape(), "Interp_C_triple_C1")
except Exception as e:
    print(f"  C1 knot insertion failed: {e}")

App.ActiveDocument.recompute()
print("\nThe end\n")
