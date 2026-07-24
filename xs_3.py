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
import control_curves
import xs_base

if False:
    importlib.reload(hf)
    #testing off, Turn on
    #importlib.reload(last_insole)
    importlib.reload(last_profile)
    importlib.reload(xs_base)

print(f"+++++++++++++++Line({inspect.currentframe().f_lineno}) File:({__file__})+++++++++++++++++++")

sketch_name = "Sketch_xs_3"
doc, sketch_xs3 = hf.Doc_Sketch(None, sketch_name)


@dataclass
class xs_3_lens_c:
    def __init__(self, p_lens:     last_profile.profile_lengths_c,
                       insole_dwg:  last_insole.insole_layout,
                       profile_dwg: last_profile.draw_profile_c):
        d = xs_base.xs_3_placement.Base.x

        self.HC = xs_base.xs_3.HC

        ptH2 = hf.line_intersect_plane(hf.nX, d, insole_dwg.J2, insole_dwg.H2)
        ptT1 = hf.line_intersect_plane(hf.nX, d, insole_dwg.J1, insole_dwg.H1)
        outline_pts = hf.get_bspline_plane_intersection_new(
            last_insole.outline_bc, App.Vector(d, 0, 0), hf.nX)
        outline_pts.sort(key=lambda p: p.y, reverse=True)
        self.HH1 = outline_pts[0].y
        self.HH2 = abs(outline_pts[1].y)
        self.TT1 = ptT1.y + 5
        self.TT2 = abs(ptH2.y)
        self.CC1 = xs_base.xs_3.CC1
        self.CC2 = xs_base.xs_3.CC2
        self.HC1 = xs_base.xs_3.HC1
        self.HC2 = xs_base.xs_3.HC2
        self.HH3 = 3

        # HT1/HT2 from medial/lateral highwater BSpline intersections
        poles_3d = [last_profile.sketch_profile.Placement.multVec(p)
                    for p in control_curves.T1_profile.getPoles()]
        med_hw_3d = Part.BSplineCurve()
        med_hw_3d.buildFromPolesMultsKnots(
            poles_3d,
            control_curves.T1_profile.getMultiplicities(),
            control_curves.T1_profile.getKnots(),
            False, control_curves.T1_profile.Degree)
        g_T1_pts = hf.get_bspline_plane_intersection_new(
            med_hw_3d,
            xs_base.xs_3_placement.Base,
            xs_base.xs_3_normal)
        g_T1 = g_T1_pts[0]
        hf.p_vec(g_T1, "xs_3 g_T1")
        self.HT1 = (g_T1 - xs_base.g_K).dot(xs_base.gvec_K_I)

        poles_3d = [last_profile.sketch_profile.Placement.multVec(p)
                    for p in control_curves.T2_profile.getPoles()]
        lat_hw_3d = Part.BSplineCurve()
        lat_hw_3d.buildFromPolesMultsKnots(
            poles_3d,
            control_curves.T2_profile.getMultiplicities(),
            control_curves.T2_profile.getKnots(),
            False, control_curves.T2_profile.Degree)
        g_T2_pts = hf.get_bspline_plane_intersection_new(
            lat_hw_3d,
            xs_base.xs_3_placement.Base,
            xs_base.xs_3_normal)
        g_T2 = g_T2_pts[0]
        hf.p_vec(g_T2, "xs_3 g_T2")
        self.HT2 = (g_T2 - xs_base.g_K).dot(xs_base.gvec_K_I)

        hf.p_vec(ptH2, "xs_3 ptH2")

    def build(self):
        sc    = xs_base.xs_3
        _H_y  = (sc.H  - xs_base.xs_3_placement.Base).dot(xs_base.gvec_K_I)
        _H3_y = (sc.H3 - xs_base.xs_3_placement.Base).dot(xs_base.gvec_K_I)
        self.H  = App.Vector(0,       _H_y,  0)
        self.H1 = App.Vector( sc.HH1, _H_y,  0)
        self.H2 = App.Vector( sc.HH2, _H_y,  0)  # HH2 negative = lateral
        self.H3 = App.Vector(0,       _H3_y, 0)
        self.T1 = App.Vector(sc.TT1,  sc.HT1, 0)
        self.T2 = App.Vector(sc.TT2,  sc.HT2, 0)
        t       = sc.TT1 / (sc.TT1 - sc.TT2)
        self.T  = App.Vector(0, sc.HT1 + t * (sc.HT2 - sc.HT1), 0)
        self.C  = App.Vector(0,        self.HC, 0)
        self.C1 = App.Vector( self.CC1, self.HC1, 0)
        self.C2 = App.Vector(-self.CC2, self.HC2, 0)
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
xs_3 = xs_3_lens_c(last_profile.p_lens,
                   last_insole.insole_dwg, last_profile.profile_dwg)
xs_3.build()
xs_3.draw_circles(sketch_xs3)
xs_3.draw_lines(sketch_xs3)


plen, plen_in = xs_3.perimeter_length()
print(f"xs_3 perimeter = {plen:.1f} mm  ({plen_in:.3f} in)")

sketch_xs3.Placement = xs_base.xs_3_placement * hf.yz_xy_place

#view = FreeCADGui.ActiveDocument.ActiveView
#view.fitAll()
#view.viewFront()
doc.recompute()
#checking
hf.p_vec(xs_3.T1,"xs_3.T1")
temp_xs_3_T1_3d = sketch_xs3.Placement.multVec(xs_3.T1)
temp_xs_3_T1_xy_3d = temp_xs_3_T1_3d.scale(1.0,1.0,0.0)
hf.p_vec(xs_3.T1,"xs_3.T1")
hf.p_vec(temp_xs_3_T1_3d,"temp_xs_3_T1_3d")
hf.p_vec(temp_xs_3_T1_3d-temp_xs_3_T1_xy_3d,"difftemp_xs_3_T1_3d")
hf.p_vec(xs_3.T2,"xs_3.T2")
hf.print_4x4_matrix(sketch_xs3.Placement.Matrix,"xs3_placement")
#sketch_xs3.addGeometry(Part.LineSegment(temp_xs_3_T1_3d,temp_xs_3_T1_xy_3d))
#end checking
print("\nThe end\n")

def main():
    print("xs_3 main")
if __name__ == "__main__":
    main()
