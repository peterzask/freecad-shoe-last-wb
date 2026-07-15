import inspect
import importlib
import FreeCAD as App
import FreeCADGui
import Part
import helper_funcs as hf
import last_insole
import last_profile
import inspect
import xs_0, xs_1, xs_2, xs_3, xs_4, xs_5, xs_6, xs_7, xs_8, xs_9
import xs_heel_near
import xs_base
import control_curves
#import analyze_uv_matrix as analyz

if True:
    importlib.reload(inspect)
    importlib.reload(hf)
    importlib.reload(last_insole)
    importlib.reload(last_profile)
    importlib.reload(control_curves)  # reloads _OVERRIDES and build() definition
    importlib.reload(xs_base)         # xs_base.build() calls control_curves.build() first
    for m in [xs_0, xs_1, xs_2, xs_3, xs_4, xs_5, xs_6, xs_7, xs_8, xs_9]:
        importlib.reload(m)
    importlib.reload(xs_heel_near)

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
    (xs_9.xs_9, xs_base.xs_9_placement),
]

def _hartley_judd_knots(params, degree):
    """Clamped BSpline knots by Hartley-Judd averaging.
    For degree=1 reproduces chord-length parameterization exactly."""
    n = len(params)
    interior = [sum(params[j:j+degree]) / degree for j in range(1, n - degree)]
    knots = [0.0] + interior + [1.0]
    mults  = [degree + 1] + [1] * len(interior) + [degree + 1]
    return knots, mults

degree = 2 #xs_base.NURBS_DEGREE

# xs_scalars_list[i].H is the girth-scale center for xs_list[i]
xs_scalars_list = [
    xs_base.xs_0, xs_base.xs_1, xs_base.xs_2, xs_base.xs_3,
    xs_base.xs_4, xs_base.xs_5, xs_base.xs_6, xs_base.xs_7, xs_base.xs_8, xs_base.xs_9,
]

# Per-section multiplier on c_scale and t_scale (applied on top of global values).
# Use to nudge one section's girth without disturbing others.
# Each 0.01 change moves girth by roughly 1-2mm (section-dependent).
_SECTION_GIRTH_SCALE = {
    'xs_4': 1.0,   # waist: pull crown/shoulder inward; target -15mm from +15.2mm excess
}
#'xs_4': 0.93,   # waist: pull crown/shoulder inward; target -15mm from +15.2mm excess

# Locked ring indices (H2 seam-start, H3, H1; seam-end added per-row)
_LOCKED_PLAIN = frozenset([0, 1, 2])   # H2, H3, H1
_LOCKED_CRISP = frozenset([0, 1, 2, 3])  # H2, H3, H1, H1(doubled)

def _apply_girth_scale(pts, h, c_scale, t_scale, crisp):
    """Expand non-sole control points outward from H; H1/H2/H3 stay locked.
    c_scale applies to C1/C/C2; t_scale applies to T1/T2 independently."""
    n = len(pts)
    locked = (_LOCKED_CRISP if crisp else _LOCKED_PLAIN) | {n - 1}
    t1_idx = 4 if crisp else 3
    t2_idx = n - 2
    result = []
    for i, p in enumerate(pts):
        if i in locked:
            result.append(p)
        elif i in (t1_idx, t2_idx):
            result.append(h + (p - h) * t_scale)
        else:
            result.append(h + (p - h) * c_scale)
    return result

# Transform each section's control points from sketch-local to global 3D
# heel_end_row prepended so degree-2 u smooths through the heel — no separate heel cap needed
_sec_names = ['xs_0','xs_1','xs_2','xs_3','xs_4','xs_5','xs_6','xs_7','xs_8','xs_9']
rows = [list(xs_base.get_heel_end_row(crisp_sole=True))]
pl_hn = xs_base.xs_heel_near_placement * hf.yz_xy_place
rows.append(xs_heel_near.xs_heel_near.row_world(pl_hn, crisp_sole=True))
for (xs, placement), xs_sc, sec_name in zip(xs_list, xs_scalars_list, _sec_names):
    pl = placement * hf.yz_xy_place
    pts = [pl.multVec(pv) for pv in xs.ctrl.control_points(crisp_sole=True)] #xs_base.CRISP_SOLE)]
    """
    if False:
        _sg  = _SECTION_GIRTH_SCALE.get(sec_name, 1.0)
        pts = _apply_girth_scale(pts, xs_sc.H,
                                 xs_base.C_SCALE * _sg, xs_base.T_SCALE * _sg,
                                 xs_base.CRISP_SOLE)
    """
    rows.append(pts)

rows.append(list(xs_base.xs_toe_end_row))

u_count = len(rows)    # 13: heel_end + xs_heel_near + 10 sections + toe_end
v_count = len(rows[0]) # 9 (or 10 with CRISP_SOLE): H2 H3 [H1 H1] T1 C1 C C2 T2 H2
#print(f"u_count={u_count}, v_count={v_count}")

# Show scaled control points as vertex markers (rows 1–9, skipping heel_end and toe_end)
if False:
    if xs_base.C_SCALE != 1.0 or xs_base.T_SCALE != 1.0:
        _ctrl_verts = [Part.Vertex(pt) for row in rows[1:-1] for pt in row]
        _ctrl_compound = Part.makeCompound(_ctrl_verts)
        _ctrl_name = "GirthScaleCtrlPts"
        if App.ActiveDocument.getObject(_ctrl_name):
            App.ActiveDocument.removeObject(_ctrl_name)
        _ctrl_obj = App.ActiveDocument.addObject("Part::Feature", _ctrl_name)
        _ctrl_obj.Shape = _ctrl_compound

if False:
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

# Chord-length parameterization in v around the xs_3 cross-section (index 5: heel_end + xs_heel_near + xs_0..xs_2)
vks_raw = [0.0]
for v in range(1, v_count):
    vks_raw.append(vks_raw[-1] + (rows[5][v] - rows[5][v-1]).Length)
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

# Build heel and toe cap surfaces as ruled surfaces (ring → centroid).
# Same vks/v_mults as the main surface → exact BSpline match at the shared boundary edge.
def _ring_cap(ring, ring_at_u0=True):
    n = len(ring) - 1  # unique poles (exclude closing repeat)
    ctr = App.Vector(
        sum(p.x for p in ring[:n]) / n,
        sum(p.y for p in ring[:n]) / n,
        sum(p.z for p in ring[:n]) / n,
    )
    ctr_row = [ctr] * len(ring)
    poles = [ring, ctr_row] if ring_at_u0 else [ctr_row, ring]
    nc = Part.BSplineSurface()
    nc.buildFromPolesMultsKnots(
        poles, [2, 2], v_mults, [0.0, 1.0], vks,
        uperiodic=False, vperiodic=False,
        udegree=1, vdegree=degree)
    return nc.toShape()

_heel_ring = list(xs_base.get_heel_end_row(crisp_sole=True)) #xs_base.CRISP_SOLE))
_toe_ring  = list(xs_base.xs_toe_end_row)
print("Toe Ring !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
print(_toe_ring)
heel_cap_shape = _ring_cap(_heel_ring, ring_at_u0=True)
toe_cap_shape  = _ring_cap(_toe_ring,  ring_at_u0=False)

last_shell = Part.makeShell([shoe_last_shape, heel_cap_shape, toe_cap_shape])
last_solid = Part.makeSolid(last_shell)
last_solid = last_solid.removeSplitter()
_solid_name = "ShoeLast"
if App.ActiveDocument.getObject(_solid_name):
    App.ActiveDocument.removeObject(_solid_name)
_solid_obj = App.ActiveDocument.addObject("Part::Feature", _solid_name)
_solid_obj.Shape = last_solid
Part.show(shoe_last_shape)    #Showing same object twice ?
#Part.show(heel_cap_shape)
App.ActiveDocument.recompute()


if True:
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



if False:
    # --- Girth check: degree-2 BSpline through post-scale 3D ring points ---
    # rows index: 0=heel_end, 1=xs_0 ... 4=xs_3(instep) 5=xs_4(waist) 6=xs_5(joint)
    # Ring closes on itself — last point == first point; drop it before periodic build.
    # degree-2 periodic BSpline matches the NURBS surface v-direction degree,
    # so arc length closely approximates the actual surface girth at each section.
    _girth_ring_data = [
        ("xs_3  instep", rows[5],  last_insole.ft_measurements.instep),
        ("xs_4  waist",  rows[6],  last_insole.ft_measurements.waist),
        ("xs_5  joint",  rows[7],  last_insole.ft_measurements.joint),
    ]
    _girth_shapes = []
    print("\n=== Girth check (deg-2 BSpline, post-scale) ===")
    print(f"  {'Section':<14}  {'Target':>8}  {'BSpline':>8}  {'Delta':>8}")
    for label, ring, target_mm in _girth_ring_data:
        # Drop closing H2, then prepend H2 again to double it — same reason CRISP_SOLE
        # doubles H1: forces the degree-2 periodic BSpline to pass through H2 instead
        # of cutting the corner inward at the lateral insole seam.
        poles = [ring[0]] + list(ring[:-1])
        bc = Part.BSplineCurve()
        bc.buildFromPoles(poles, True, degree, False)   # periodic, same degree as surface
        arc_mm  = bc.length()
        arc_in  = arc_mm / 25.4
        delta   = arc_mm - target_mm
        sign    = "+" if delta >= 0 else ""
        print(f"  {label:<14}  {target_mm:>7.1f}mm  {arc_mm:>7.1f}mm  {sign}{delta:.1f}mm  ({arc_in:.3f}in)")
        _girth_shapes.append(bc.toShape())
    _girth_compound = Part.makeCompound(_girth_shapes)
    _girth_name     = "GirthCheckRings"
    #_g_obj = App.ActiveDocument.getObject(_girth_name) or \
    #         App.ActiveDocument.addObject("Part::Feature", _girth_name)
    #_g_obj.Shape = _girth_compound
    #_sg_str = "  ".join(f"{k}={v:.3f}" for k,v in _SECTION_GIRTH_SCALE.items()) or "none"
    #print(f"  t_scale={xs_base.T_SCALE:.3f}  c_scale={xs_base.C_SCALE:.3f}  sec_girth_scale: {_sg_str}  rings='{_girth_name}'")
    #print("=== positive delta = last larger than foot girth ===\n")

print("\nThe end\n")


def main():
    print("uv_0 main")
if __name__ == "__main__":
    main()
