import inspect
import importlib
import FreeCAD as App
import FreeCADGui
import Part
import helper_funcs as hf
import last_insole
import last_profile
import inspect
import xs_0, xs_1, xs_2, xs_3, xs_4, xs_5, xs_6, xs_7, xs_8
import xs_base
#import analyze_uv_matrix as analyz

if True:
    importlib.reload(inspect)
    importlib.reload(hf)
    importlib.reload(last_insole)
    importlib.reload(last_profile)
    importlib.reload(xs_base)
    for m in [xs_0, xs_1, xs_2, xs_3, xs_4, xs_5, xs_6, xs_7, xs_8]:
        importlib.reload(m)

print(f"+++++++++++++++Line({inspect.currentframe().f_lineno}) File:({__file__})+++++++++++++++++++")

# Sections in heel-to-toe order with their placements
xs_list = [
    (xs_0.xs_0, xs_base.xs_0_placement),
    (xs_1.xs_1, xs_base.xs_1_placement),
    (xs_2.xs_2, xs_base.xs_2_placement),
    (xs_3.xs_3, xs_base.xs_3_placement),
    (xs_4.xs_4, xs_base.xs_4_placement),
    (xs_5.xs_5, xs_base.xs_5_placement),
    (xs_6.xs_6, xs_base.xs_6_placement),
    (xs_7.xs_7, xs_base.xs_7_placement),
    (xs_8.xs_8, xs_base.xs_8_placement),
]

def _hartley_judd_knots(params, degree):
    """Clamped BSpline knots by Hartley-Judd averaging.
    For degree=1 reproduces chord-length parameterization exactly."""
    n = len(params)
    interior = [sum(params[j:j+degree]) / degree for j in range(1, n - degree)]
    knots = [0.0] + interior + [1.0]
    mults  = [degree + 1] + [1] * len(interior) + [degree + 1]
    return knots, mults

degree = xs_base.NURBS_DEGREE

# xs_scalars_list[i].H is the girth-scale center for xs_list[i]
xs_scalars_list = [
    xs_base.xs_0, xs_base.xs_1, xs_base.xs_2, xs_base.xs_3,
    xs_base.xs_4, xs_base.xs_5, xs_base.xs_6, xs_base.xs_7, xs_base.xs_8,
]

# Locked ring indices (H2 seam-start, H3, H1; seam-end added per-row)
_LOCKED_PLAIN = frozenset([0, 1, 2])   # H2, H3, H1
_LOCKED_CRISP = frozenset([0, 1, 2, 3])  # H2, H3, H1, H1(doubled)

def _apply_girth_scale(pts, h, scale, crisp, t_boost_mm=0.0):
    """Expand T1/C1/C/C2/T2 outward from H; leave H1/H2/H3 (insole footprint) fixed.
    t_boost_mm adds a direct mm nudge to T1 and T2 on top of scale — they pull in
    more than C/C1/C2 due to higher ring curvature at the sole-to-crown shoulder."""
    n = len(pts)
    locked = (_LOCKED_CRISP if crisp else _LOCKED_PLAIN) | {n - 1}
    t1_idx = 4 if crisp else 3
    t2_idx = n - 2
    result = []
    for i, p in enumerate(pts):
        if i in locked:
            result.append(p)
        else:
            d = p - h
            scaled = h + d * scale
            if t_boost_mm and i in (t1_idx, t2_idx):
                dl = d.Length
                scaled = scaled + d * (t_boost_mm / dl) if dl > 0 else scaled
            result.append(scaled)
    return result

# Transform each section's control points from sketch-local to global 3D
# heel_end_row prepended so degree-2 u smooths through the heel — no separate heel cap needed
rows = [list(xs_base.get_heel_end_row(crisp_sole=xs_base.CRISP_SOLE))]
for (xs, placement), xs_sc in zip(xs_list, xs_scalars_list):
    pl = placement * hf.yz_xy_place
    pts = [pl.multVec(pv) for pv in xs.ctrl.control_points(crisp_sole=xs_base.CRISP_SOLE)]
    pts = _apply_girth_scale(pts, xs_sc.H, xs_base.GIRTH_SCALE, xs_base.CRISP_SOLE, xs_base.T_BOOST_MM)
    rows.append(pts)

pl = xs_base.xs_toe_end_placement * hf.yz_xy_place
rows.append([pl.multVec(pv) for pv in xs_base.xs_toe_end.control_points(crisp_sole=xs_base.CRISP_SOLE)])

u_count = len(rows)    # 11: heel_end + 9 sections + toe_end
v_count = len(rows[0]) # 9 (or 10 with CRISP_SOLE): H2 H3 [H1 H1] T1 C1 C C2 T2 H2
print(f"u_count={u_count}, v_count={v_count}")

# Show scaled control points as vertex markers (rows 1–9, skipping heel_end and toe_end)
if xs_base.GIRTH_SCALE != 1.0:
    _ctrl_verts = [Part.Vertex(pt) for row in rows[1:-1] for pt in row]
    _ctrl_compound = Part.makeCompound(_ctrl_verts)
    _ctrl_name = "GirthScaleCtrlPts"
    if App.ActiveDocument.getObject(_ctrl_name):
        App.ActiveDocument.removeObject(_ctrl_name)
    _ctrl_obj = App.ActiveDocument.addObject("Part::Feature", _ctrl_name)
    _ctrl_obj.Shape = _ctrl_compound

for u, row in enumerate(rows):
    for v, pv in enumerate(row):
        hf.p_vec(pv, f"  [{u},{v}]")

# Chord-length parameterization in u along the C-point spine (C is at v_count//2 + 1)
C_idx = v_count // 2 + 1
uks_raw = [0.0]
for u in range(1, u_count):
    uks_raw.append(uks_raw[-1] + (rows[u][C_idx] - rows[u-1][C_idx]).Length)
uks_raw = [k / uks_raw[-1] for k in uks_raw]
uks, u_mults = _hartley_judd_knots(uks_raw, degree)

# Chord-length parameterization in v around the xs_3 cross-section (index 4 with heel row prepended)
vks_raw = [0.0]
for v in range(1, v_count):
    vks_raw.append(vks_raw[-1] + (rows[4][v] - rows[4][v-1]).Length)
vks_raw = [k / vks_raw[-1] for k in vks_raw]
vks, v_mults = _hartley_judd_knots(vks_raw, degree)

print(f"uks    = {[f'{k:.3f}' for k in uks]}")
print(f"vks    = {[f'{k:.3f}' for k in vks]}")
print(f"u_mults= {u_mults}")
print(f"v_mults= {v_mults}")

nurb = Part.BSplineSurface()
nurb.buildFromPolesMultsKnots(
    rows, u_mults, v_mults, uks, vks,
    uperiodic=False, vperiodic=False,
    udegree=degree, vdegree=degree)
shoe_last_shape = nurb.toShape()

# --- Toe tip cap surface: ruled from xs_toe_end ring to g_B1 ---
toe_rows = [
    rows[-1],                                    # xs_toe_end — shared boundary with main surface
    [App.Vector(xs_base.g_B1)] * v_count,        # B1 — all poles converge to toe tip
]
tc_uks     = [0.0, 1.0]
tc_u_mults = [2, 2]

toe_nurb = Part.BSplineSurface()
toe_nurb.buildFromPolesMultsKnots(
    toe_rows, tc_u_mults, v_mults, tc_uks, vks,
    uperiodic=False, vperiodic=False,
    udegree=1, vdegree=degree)
toe_cap_shape = toe_nurb.toShape()

last_shell = Part.makeShell([shoe_last_shape, toe_cap_shape])
last_solid = Part.makeSolid(last_shell)
last_solid = last_solid.removeSplitter()
Part.show(last_solid)
#Part.show(shoe_last_shape)
#Part.show(heel_cap_shape)
App.ActiveDocument.recompute()

import os
import MeshPart
_dir = os.path.dirname(os.path.abspath(__file__))
step_path = os.path.join(_dir, "shoe_last.step")
last_solid.exportStep(step_path)
print(f"Exported STEP: {step_path}")
stl_path = os.path.join(_dir, "shoe_last.stl")
mesh = MeshPart.meshFromShape(Shape=last_solid, LinearDeflection=0.3, AngularDeflection=0.5)
mesh.write(stl_path)
print(f"Exported STL:  {stl_path}")



print("\nThe end\n")


def main():
    print("uv_0 main")
if __name__ == "__main__":
    main()
