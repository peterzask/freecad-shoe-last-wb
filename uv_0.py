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

# Transform each section's control points from sketch-local to global 3D
# heel_end_row prepended so degree-2 u smooths through the heel — no separate heel cap needed
rows = [list(xs_base.get_heel_end_row(crisp_sole=xs_base.CRISP_SOLE))]
for xs, placement in xs_list:
    pl = placement * hf.yz_xy_place
    rows.append([pl.multVec(pv) for pv in xs.ctrl.control_points(crisp_sole=xs_base.CRISP_SOLE)])

pl = xs_base.xs_toe_end_placement * hf.yz_xy_place
rows.append([pl.multVec(pv) for pv in xs_base.xs_toe_end.control_points(crisp_sole=xs_base.CRISP_SOLE)])

u_count = len(rows)    # 11: heel_end + 9 sections + toe_end
v_count = len(rows[0]) # 9 (or 11 with CRISP_SOLE): H3 [H2 H2] T2 C2 C C1 T1 [H1 H1] H3
print(f"u_count={u_count}, v_count={v_count}")

for u, row in enumerate(rows):
    for v, pv in enumerate(row):
        hf.p_vec(pv, f"  [{u},{v}]")

# Chord-length parameterization in u along the C-point spine (v_count//2 = C index)
C_idx = v_count // 2
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
