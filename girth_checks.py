"""Feedback measurements: built-last girth/perimeter vs. target foot measurements.

First cut — one place for the numbers, format/scope still open. Run after
xs_0..xs_9 and uv_0.py (needs the "ShoeLast" solid) have built in this session.
"""
import inspect
import FreeCAD as App
import Part
import helper_funcs as hf
import last_profile
import last_insole
import xs_0, xs_1, xs_2, xs_3, xs_4, xs_5, xs_6, xs_7, xs_8, xs_9, uv_0
import xs_base


# --- Measurement planes for stations with no dedicated cross-section macro
# (heel, high instep, joint) — folded in from the retired sandbox_a.py. ---

def build_Kb_H1_High_Instep_Plane():
    V = App.Vector
    pr_Kb = last_profile.sketch_profile.Placement.multVec(last_profile.profile_dwg.Kb)
    pr_H1 = last_profile.sketch_profile.Placement.multVec(last_profile.profile_dwg.H1)
    dimX = 80
    dimY = 120

    planeShape = Part.makePlane(dimX, dimY, V(-dimX / 2, -5, 0), hf.nZ, hf.nX)
    p1 = hf.yz_xy_place
    dirZ = (pr_H1 - pr_Kb).normalize()
    p2 = App.Placement(pr_Kb, App.Rotation(hf.nZ, dirZ))
    planeShape.Placement = p2 * p1
    name_str = "High_Instep_Plane"
    doc = last_profile.sketch_profile.Document
    if doc.getObject(name_str):
        doc.removeObject(name_str)
    planeObject = doc.addObject("Part::Feature", name_str)
    planeObject.Shape = planeShape
    return planeObject


def build_H_H1_Heel_Plane():
    V = App.Vector
    pr_H = last_profile.sketch_profile.Placement.multVec(last_profile.profile_dwg.H)
    pr_H1 = last_profile.sketch_profile.Placement.multVec(last_profile.profile_dwg.H1)
    dimX = 80
    dimY = 180

    planeShape = Part.makePlane(dimX, dimY, V(-dimX / 2, -5, 0), hf.nZ, hf.nX)
    p1 = hf.yz_xy_place
    dirZ = (pr_H1 - pr_H).normalize()
    p2 = App.Placement(pr_H, App.Rotation(hf.nZ, dirZ))
    planeShape.Placement = p2 * p1
    name_str = "Heel_Plane"
    doc = last_profile.sketch_profile.Document
    if doc.getObject(name_str):
        doc.removeObject(name_str)
    planeObject = doc.addObject("Part::Feature", name_str)
    planeObject.Shape = planeShape
    return planeObject


def build_J1_J2_Joint_Plane():
    V = App.Vector
    in_J1 = V(last_insole.insole_dwg.J1)
    in_J2 = V(last_insole.insole_dwg.J2)
    in_J = V(last_insole.insole_dwg.J)
    pr_J1 = last_profile.sketch_profile.Placement.multVec(last_profile.profile_dwg.J1)
    widthX = 130
    widthY = 75
    # build plane in default x-y plane,
    # translate to center x-direction and move y by -5mm to cover below
    planeShape = Part.makePlane(widthX, widthY, V(-widthX / 2, -5, 0), hf.nZ, hf.nX)
    # 3 rotations and 1 translation
    # rotate to yz plane
    p1 = hf.yz_xy_place
    # tilt it forward
    dirZ = (pr_J1 - in_J).normalize()
    p2 = App.Placement(V(0, 0, 0), App.Rotation(hf.nZ, dirZ))
    # tilt y-axis to joint line (in_J1-in_J2) , then translate in_J
    dirY = (in_J1 - in_J2).normalize()
    p3 = App.Placement(in_J, App.Rotation(hf.nY, dirY))
    planeShape.Placement = p3 * p2 * p1
    name_str = "Ball_Joint_Plane"  # mechanical foot humor
    doc = last_profile.sketch_profile.Document
    if doc.getObject(name_str):
        doc.removeObject(name_str)
    planeObject = doc.addObject("Part::Feature", name_str)
    planeObject.Shape = planeShape
    return planeObject


Heel_Plane_Object = build_H_H1_Heel_Plane()
High_Instep_Plane_Object = build_Kb_H1_High_Instep_Plane()
ball_joint_plane_object = build_J1_J2_Joint_Plane()


# Collected here as each station is measured, printed as one summary block
# by _print_summary_table() at the end — see that function for why.
_RESULTS = []


def _report_girth(doc, name, girth_mm, target_mm, section_edges):
    if not section_edges:
        print(f"girth_checks: {name} plane/last section produced no edges")
        _RESULTS.append((name, None, target_mm))
        return
    if target_mm is None:
        print(f"{name} girth = {girth_mm:.1f}mm  ({girth_mm / 25.4:.3f}in)  (no target on file)")
    else:
        delta = girth_mm - target_mm
        sign = "+" if delta >= 0 else ""
        print(f"{name} girth = {girth_mm:.1f}mm  target = {target_mm:.1f}mm  "
              f"delta = {sign}{delta:.1f}mm  ({girth_mm / 25.4:.3f}in)")
    _RESULTS.append((name, girth_mm, target_mm))

    sec_name = f"{name}_section"
    if doc.getObject(sec_name):
        doc.removeObject(sec_name)
    sec_obj = doc.addObject("Part::Feature", sec_name)
    sec_obj.Shape = Part.Compound(section_edges)


def _print_summary_table(results):
    # Report View timestamps each print() call individually, which chops a
    # multi-line table apart. Building the whole table as one string (old
    # %-style formatting, not f-strings, per request) and calling print()
    # ONCE sidesteps that — it lands as a single untouched block.
    header = "%-18s %10s %10s %10s %10s" % (
        "Station", "Girth(mm)", "Target(mm)", "Delta(mm)", "Girth(in)")
    rule = "-" * len(header)
    lines = [header, rule]
    for name, girth_mm, target_mm in results:
        if girth_mm is None:
            lines.append("%-18s %10s %10s %10s %10s" % (name, "no edges", "-", "-", "-"))
            continue
        girth_in = girth_mm / 25.4
        if target_mm is None:
            lines.append("%-18s %10.1f %10s %10s %10.3f" % (name, girth_mm, "-", "-", girth_in))
        else:
            delta = girth_mm - target_mm
            lines.append("%-18s %10.1f %10.1f %+10.1f %10.3f" % (name, girth_mm, target_mm, delta, girth_in))
    print("\n=== Girth summary (heel to toe) ===\n%s\n" % "\n".join(lines))


def _measure_girth_from_plane(doc, last_obj, name, plane_obj, target_mm):
    """Section last_obj with an already-built plane object (e.g. from build_H_H1_Heel_Plane above)."""
    section = last_obj.Shape.section(plane_obj.Shape)
    # Sum every edge, not just the longest connected wire — see _measure_girth.
    girth_mm = sum(e.Length for e in section.Edges) if section.Edges else 0.0
    _report_girth(doc, name, girth_mm, target_mm, section.Edges)


def _measure_girth(doc, last_obj, name, origin, normal, target_mm, L=250, W=150):
    """Section last_obj with a plane at origin/normal; print + show the girth wire."""
    # Local plane built with normal=hf.nZ (not hf.nX — that was the actual
    # bug: App.Rotation(hf.nZ, normal) below maps local Z to the target
    # direction, so the plane's own local normal must be Z too, or the
    # rotation carries a different local axis to `normal` and the resulting
    # cutting plane ends up ~90 deg off from intended. Verified empirically
    # 2026-07-27: with local normal=hf.nX this was off by 90 deg; with
    # local normal=hf.nZ the placed face's actual normal matches exactly.
    # Centered on the origin (not offset from a corner) so the rectangle's
    # footprint is guaranteed to surround the origin regardless of normal.
    plane_shape = Part.makePlane(L, W, App.Vector(-L / 2, -W / 2, 0), hf.nZ, hf.nX)
    plane_name = f"{name}_plane"
    if doc.getObject(plane_name):
        doc.removeObject(plane_name)
    plane_object = doc.addObject("Part::Feature", plane_name)
    plane_object.Shape = plane_shape
    # plane_object.Shape (not plane_shape) so the Placement below is baked in.
    plane_object.Placement = App.Placement(origin, App.Rotation(hf.nZ, normal))

    section = last_obj.Shape.section(plane_object.Shape)
    # Sum every edge, not just the longest connected wire — the solid is
    # stitched from multiple patches (main surface + heel/toe caps), so a
    # cutting plane crossing a seam splits the true loop into 2+ edges that
    # share endpoints but aren't always recognized as one continuous wire.
    # "Longest wire only" silently discarded the other piece(s) — confirmed
    # on Ball_Joint_Plane: 93.49mm + 163.73mm (same shared vertices) sum to
    # 257.2mm, matching xs_5's independent 262.1mm estimate; longest-alone
    # gave a wrong 164.1mm.
    girth_mm = sum(e.Length for e in section.Edges) if section.Edges else 0.0
    _report_girth(doc, name, girth_mm, target_mm, section.Edges)



print(f"+++++++++++++++Line({inspect.currentframe().f_lineno}) File:({__file__})+++++++++++++++++++")

V = App.Vector

doc = last_profile.doc

# --- Sketch perimeter (straight-line control-point polygon) per section ---
print(f"xs_1 perimeter        = {xs_1.plen:4.2f},{xs_1.plen_in:4.2f}")
print(f"xs_2 perimeter        = {xs_2.plen:4.2f},{xs_2.plen_in:4.2f}")
print(f"xs_3 perimeter instep = {xs_3.plen:4.2f},{xs_3.plen_in:4.2f}")
print(f"xs_4 perimeter waist  = {xs_4.plen:4.2f},{xs_4.plen_in:4.2f}")
print(f"xs_5 perimeter joint  = {xs_5.plen:4.2f},{xs_5.plen_in:4.2f}")
print(f"xs_6 perimeter = {xs_6.plen:4.2f},{xs_6.plen_in:4.2f}")
print(f"xs_7 perimeter = {xs_7.plen:4.2f},{xs_7.plen_in:4.2f}")
print(f"xs_8 perimeter = {xs_8.plen:4.2f},{xs_8.plen_in:4.2f}")
print(f"xs_9 perimeter = {xs_9.plen:4.2f},{xs_9.plen_in:4.2f}")

last_obj = doc.getObject("ShoeLast")
if last_obj is None:
    print("girth_checks: 'ShoeLast' not in document yet — run uv_0.py first")
else:
    ft = last_insole.ft_measurements
    print("\n=== Girth checks, heel to toe (per comments.txt) ===")

    # --- 1) Heel — build_H_H1_Heel_Plane, plane through H/H1 ---
    _measure_girth_from_plane(doc, last_obj, "Heel_meas",
                              Heel_Plane_Object, ft.heel)

    # --- 2) High instep — build_Kb_H1_High_Instep_Plane ---
    _measure_girth_from_plane(doc, last_obj, "High_Instep_meas",
                              High_Instep_Plane_Object, ft.h_instep)

    # --- 3) Instep — xs_3's own placement (K_I_Instep_Plane) ---
    _measure_girth(doc, last_obj, "Instep_meas",
                   xs_base.xs_3_placement.Base, xs_base.xs_3_normal, ft.instep)

    # --- 4) Waist — xs_4's own placement ---
    _measure_girth(doc, last_obj, "Waist_meas",
                   xs_base.xs_4_placement.Base, xs_base.xs_4_normal, ft.waist)

    # --- 5) Joint — build_J1_J2_Joint_Plane above. Origin at the insole
    # J1/J2 midpoint, tilted onto the J1-J2 line and toward profile J1 —
    # NOT a plane forced through all 3 points exactly, which was tried
    # first and rejected: those are construction/design reference points,
    # not points on the actual (shrunk-hull) built surface, so a plane
    # anchored to all three cut the real solid at a bad angle (open wire,
    # 2 disconnected chains). Checked 2026-07-27.
    _measure_girth_from_plane(doc, last_obj, "Joint_meas",
                              ball_joint_plane_object, ft.joint)

    # --- 6) Ball-across — xs_5's own placement (Ball_Across_Plane). Same
    # physical "joint girth" as #5 above, different construction — compare
    # the two deltas against each other, not just against target. ---
    _measure_girth(doc, last_obj, "Ball_Across_meas",
                   xs_base.xs_5_placement.Base, xs_base.xs_5_normal, ft.joint)

    # --- 7) Lesser-toe / 1st MTP joint — xs_6's own placement. No dedicated
    # ft_measurements field for this station; reported without a target. ---
    _measure_girth(doc, last_obj, "LToe_Joint_meas",
                   xs_base.xs_6_placement.Base, xs_base.xs_6_normal, None)

    # --- 8) Big-toe joint — xs_7's own placement. Same: no target on file. ---
    _measure_girth(doc, last_obj, "BToe_Joint_meas",
                   xs_base.xs_7_placement.Base, xs_base.xs_7_normal, None)

    _print_summary_table(_RESULTS)








print("\nThe end\n")

doc.recompute()

def main():
    print("girth_checks main")
if __name__ == "__main__":
    main()




"""
#xs_3 fit checking

class xs_3_check:
    xForm = xs_3.sketch_xs3.Placement.multVec
    #last_profile.sketch_profile.Placement.multVec
    xs_3_l_pole_list=[V(xs_3.xs_3.H2),V(xs_3.xs_3.T2),V(xs_3.xs_3.C2),V(xs_3.xs_3.C),
                      V(xs_3.xs_3.C1),V(xs_3.xs_3.T1),V(xs_3.xs_3.H1),V(xs_3.xs_3.H1),
                      V(xs_3.xs_3.H3),V(xs_3.xs_3.H2)] 
    xs_3_l_pole_list_names =["H2","T2","C2","C","C1","T1","H1","H1","H","H2"]
    sf = 9.75/9.18
    for k, p in enumerate(xs_3_l_pole_list):
        #hf.p_vec(xForm(p),xs_3_l_pole_list_names[k])
        xs_3_l_pole_list[k] = (p-xs_3_l_pole_list[8])*sf + xs_3_l_pole_list[8]
    xs_3_bsc = Part.BSplineCurve()
    xs_3_bsc.buildFromPoles(xs_3_l_pole_list,True, 2, False)
    xs_3.sketch_xs3.addGeometry(xs_3_bsc)
    len_xs_3 = xs_3_bsc.length()
    #print(f"xs_3 LENGTH = {len_xs_3}mm, {len_xs_3/25.4}in")
    #print(f"Measurement Instep Input ={last_insole.ft_measurements.instep}mm, {last_insole.ft_measurements.instep/25.4}in")
    

#xs_3 fit checking

def _hartley_judd_knots(params, degree):
    n = len(params)
    interior = [sum(params[j:j+degree]) / degree for j in range(1, n - degree)]
    knots = [0.0] + interior + [1.0]
    mults  = [degree + 1] + [1] * len(interior) + [degree + 1]
    return knots, mults
def _dedupe_v_columns(rows, ref_row_idx, tol=1e-9):
    # crisp_sole=True doubles H1 back-to-back (zero chord length). At degree 1
    # _hartley_judd_knots has no averaging to blur that into a merely-close
    # pair of knots — it comes out an exact duplicate, which OCCT rejects
    # ("VKnots interval values too close"). Drop the duplicate column from
    # every row so poles/knots stay consistent.
    ref = rows[ref_row_idx]
    keep = [0]
    for v in range(1, len(ref)):
        if (ref[v] - ref[keep[-1]]).Length > tol:
            keep.append(v)
    return [[row[v] for v in keep] for row in rows]
"""
