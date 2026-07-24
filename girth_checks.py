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
import xs_0, xs_1, xs_2, xs_3, xs_4, xs_5, xs_6, xs_7, xs_8, xs_9

print(f"+++++++++++++++Line({inspect.currentframe().f_lineno}) File:({__file__})+++++++++++++++++++")

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

# --- Heel girth: actual ShoeLast solid, sectioned by a plane through H/H1 ---
V = App.Vector
p_H1 = last_profile.sketch_profile.Placement.multVec(last_profile.profile_dwg.H1)
p_H  = last_profile.sketch_profile.Placement.multVec(last_profile.profile_dwg.H)
p_orig = p_H + (p_H1 - p_H) * (-.1)
p_axis = (p_H1 - p_H).normalize()
L = 250; W = 150
plane_shape = Part.makePlane(L, W, V(0, W / 2, 0), hf.nX, hf.nZ)

name = "Heel_meas_plane"
if doc.getObject(name):
    doc.removeObject(name)
plane_object = doc.addObject("Part::Feature", name)
plane_object.Shape = plane_shape
plane_object.Placement = App.Placement(p_orig, App.Rotation(hf.nZ, p_axis))   
doc.recompute()                                                              

last_obj = doc.getObject("ShoeLast")
if last_obj is None:
    print("girth_checks: 'ShoeLast' not in document yet — run uv_0.py first")
else:
    # plane_object.Shape (not plane_shape) so the Placement above is baked in.
    section = last_obj.Shape.section(plane_object.Shape)
    if not section.Edges:
        print("girth_checks: heel plane/last section produced no edges")
    else:
        # section.Edges are unordered/unconnected; sort into wire(s) and
        # take the longest — that's the actual girth loop, not a stray sliver.
        wires = Part.__sortEdges__(section.Edges)
        girth_wire = max((Part.Wire(w) for w in wires), key=lambda w: w.Length)
        girth_mm  = girth_wire.Length
        target_mm = last_insole.ft_measurements.heel
        delta     = girth_mm - target_mm
        sign      = "+" if delta >= 0 else ""
        print(f"heel girth = {girth_mm:.1f}mm  target = {target_mm:.1f}mm  "
              f"delta = {sign}{delta:.1f}mm  ({girth_mm / 25.4:.3f}in)")

        sec_name = "Heel_meas_section"
        if doc.getObject(sec_name):
            doc.removeObject(sec_name)
        sec_obj = doc.addObject("Part::Feature", sec_name)
        sec_obj.Shape = girth_wire

doc.recompute()
print("\nThe end\n")


def main():
    print("girth_checks main")
if __name__ == "__main__":
    main()
