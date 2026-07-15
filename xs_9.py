import inspect
import importlib
import FreeCAD as App
import FreeCADGui
import Part
import Sketcher
from dataclasses import dataclass
import helper_funcs as hf
import last_insole
import last_profile
import xs_base

if False:
    importlib.reload(hf)
    importlib.reload(last_insole)
    importlib.reload(last_profile)
    importlib.reload(xs_base)

print(f"+++++++++++++++Line({inspect.currentframe().f_lineno}) File:({__file__})+++++++++++++++++++")


sketch_name = "Sketch_xs_9"
doc, sketch_xs9 = hf.Doc_Sketch(None, sketch_name)


@dataclass
class xs_9_lens_c:
    def __init__(self, p_lens:     last_profile.profile_lengths_c,
                       insole_dwg:  last_insole.insole_layout,
                       profile_dwg: last_profile.draw_profile_c):
        # HC from toe_profile/xs_9 plane intersection
        g_C = hf.get_bspline_plane_intersection_new(
            xs_base.bc_3d_front_top,
            xs_base.xs_9_placement.Base, xs_base.gvec_uJB1)[0]
        self.HC  = (g_C - xs_base.xs_9_placement.Base).dot(xs_base.gvec_uJB1_localY)
        self.CC1 = xs_base.xs_9.CC1
        self.CC2 = xs_base.xs_9.CC2
        self.HC1 = xs_base.xs_9.HC1
        self.HC2 = xs_base.xs_9.HC2

    def build(self):
        sc    = xs_base.xs_9
        # H/H3 from bc_3d_bottom is unreliable this close to B1; use g_B1 height directly.
        # +3mm along local_up for feather-edge taper at toe tip.
        _B1_y = (xs_base.g_B1 - xs_base.xs_9_placement.Base).dot(xs_base.gvec_uJB1_localY)
        _H_y  = _B1_y + 3.0
        _H3_y = _B1_y + 3.0
        self.H  = App.Vector(0,       _H_y,  0)
        self.H1 = App.Vector( sc.HH1, _H_y,  0)
        self.H2 = App.Vector( sc.HH2, _H_y,  0)
        self.H3 = App.Vector(0,       _H3_y, 0)
        self.T1 = App.Vector( sc.TT1, sc.HT1, 0)
        self.T2 = App.Vector( sc.TT2, sc.HT2, 0)
        t       = sc.TT1 / (sc.TT1 - sc.TT2)
        self.T  = App.Vector(0, sc.HT1 + t * (sc.HT2 - sc.HT1), 0)
        self.C  = App.Vector(0,        self.HC, 0)
        self.C1 = App.Vector( self.CC1, self.HC1, 0)
        self.C2 = App.Vector(-self.CC2, self.HC2, 0)
        # TT2 comes from locus fallback (xs_9 is beyond sampled range); can be less
        # lateral than CC2, inverting the v-direction and causing a fold in quad faces.
        if self.T2.x > self.C2.x:
            self.T2 = App.Vector(self.C2.x - 0.5, self.T2.y, 0)
        self.ctrl = xs_base.xs_ctrl_pts_c(
            H3=self.H3, H=self.H,  H1=self.H1, H2=self.H2,
            T=self.T,   T1=self.T1, T2=self.T2,
            C=self.C,   C1=self.C1, C2=self.C2)
        self.control_points = self.ctrl.control_points()

    def perimeter_length(self):
        segs = [(self.H1, self.T1), (self.T1, self.C1), (self.C1, self.C),
                (self.C,  self.C2), (self.C2, self.T2), (self.T2, self.H2),
                (self.H2, self.H3), (self.H3, self.H1)]
        total = sum((b - a).Length for a, b in segs)
        return total, total / 25.4

    def draw_circles(self, sketch):
        for pt in [self.H, self.H1, self.H2, self.H3,
                   self.T, self.T1, self.T2, self.C, self.C1, self.C2]:
            sketch.addGeometry(Part.Circle(pt, hf.nZ, 2))

    def draw_lines(self, sketch):
        sketch.addGeometry(Part.LineSegment(self.C,  self.C2))
        sketch.addGeometry(Part.LineSegment(self.C2, self.T2))
        sketch.addGeometry(Part.LineSegment(self.T2, self.H2))
        sketch.addGeometry(Part.LineSegment(self.H2, self.H3))
        sketch.addGeometry(Part.LineSegment(self.H3, self.H1))
        sketch.addGeometry(Part.LineSegment(self.H1, self.T1))
        sketch.addGeometry(Part.LineSegment(self.T1, self.C1))
        sketch.addGeometry(Part.LineSegment(self.C1, self.C))


# --- Build and draw ---
xs_9 = xs_9_lens_c(last_profile.p_lens,
                   last_insole.insole_dwg, last_profile.profile_dwg)
xs_9.build()
xs_9.draw_circles(sketch_xs9)
xs_9.draw_lines(sketch_xs9)

plen, plen_in = xs_9.perimeter_length()
print(f"xs_9 perimeter = {plen:.1f} mm  ({plen_in:.3f} in)")

sketch_xs9.Placement = xs_base.xs_9_placement * hf.yz_xy_place

view = FreeCADGui.ActiveDocument.ActiveView
view.fitAll()
view.viewFront()
doc.recompute()

print("\nThe end\n")


def main():
    print("xs_9 main")
if __name__ == "__main__":
    main()
