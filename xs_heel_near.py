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
import inspect

if False:
    importlib.reload(hf)
    importlib.reload(last_insole)
    importlib.reload(last_profile)
    importlib.reload(xs_base)

print(f"+++++++++++++++Line({inspect.currentframe().f_lineno}) File:({__file__})+++++++++++++++++++")

sketch_name = "Sketch_xs_heel_near"
doc, sketch_hn = hf.Doc_Sketch(None, sketch_name)


@dataclass
class xs_heel_near_lens_c:
    def __init__(self, p_lens:     last_profile.profile_lengths_c,
                       insole_dwg:  last_insole.insole_layout,
                       profile_dwg: last_profile.draw_profile_c):
        self.HC  = xs_base.xs_heel_near.HC

        # HT1/HT2: shift bc_3d_heel 5mm forward along H→D, then find the nearest point to
        # medial_highwater_bc.  bc_3d_heel alone lies entirely behind xs_heel_near's plane;
        # the 5mm shift (from sandbox-3 experiment) brings C5 into range of the highwater locus.
        _origin = xs_base.xs_heel_near_placement.Base
        _p_uHD = (last_insole.insole_dwg.D - xs_base.g_H).normalize()
        _heel_shifted = xs_base.bc_3d_heel.copy()
        _heel_shifted.translate(_p_uHD * 5.0)
        _bc_hw_med = control_curves._bc_to_3d(control_curves.medial_highwater_bc)
        _p1, _ = hf.dist_bsc2bsc(_heel_shifted, _bc_hw_med)
        _ht = (_p1 - _origin).dot(xs_base.gvec_uHC5)
        print(f"xs_heel_near HT1={_ht:.2f} (shifted heel×hw_med)")
        self.HT1 = _ht
        self.HT2 = _ht
        self.CC1 = xs_base.xs_heel_near.CC1
        self.CC2 = xs_base.xs_heel_near.CC2
        self.HC1 = xs_base.xs_heel_near.HC1
        self.HC2 = xs_base.xs_heel_near.HC2

    def build(self):
        sc    = xs_base.xs_heel_near
        _H_y  = (sc.H  - xs_base.xs_heel_near_placement.Base).dot(xs_base.gvec_uHC5)
        _H3_y = (sc.H3 - xs_base.xs_heel_near_placement.Base).dot(xs_base.gvec_uHC5)
        self.H  = App.Vector(0,       _H_y,  0)
        self.H1 = App.Vector( sc.HH1, _H_y,  0)
        self.H2 = App.Vector( sc.HH2, _H_y,  0)
        self.H3 = App.Vector(0,       _H3_y, 0)
        self.T1 = App.Vector( sc.TT1, self.HT1, 0)
        self.T2 = App.Vector( sc.TT2, self.HT2, 0)
        t       = sc.TT1 / (sc.TT1 - sc.TT2)
        self.T  = App.Vector(0, self.HT1 + t * (self.HT2 - self.HT1), 0)
        self.C  = App.Vector(0,         self.HC,  0)
        self.C1 = App.Vector( self.CC1, self.HC1, 0)
        self.C2 = App.Vector(-self.CC2, self.HC2, 0)
        self.ctrl = xs_base.xs_ctrl_pts_c(
            H3=self.H3, H=self.H,  H1=self.H1, H2=self.H2,
            T=self.T,   T1=self.T1, T2=self.T2,
            C=self.C,   C1=self.C1, C2=self.C2)
        self.control_points = self.ctrl.control_points()

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
xs_heel_near = xs_heel_near_lens_c(last_profile.p_lens,
                                    last_insole.insole_dwg,
                                    last_profile.profile_dwg)
xs_heel_near.build()
xs_heel_near.draw_circles(sketch_hn)
xs_heel_near.draw_lines(sketch_hn)

sketch_hn.Placement = xs_base.xs_heel_near_placement * hf.yz_xy_place

view = FreeCADGui.ActiveDocument.ActiveView
view.fitAll()
view.viewFront()
doc.recompute()

print("\nThe end\n")


def main():
    print("xs_heel_near main")
if __name__ == "__main__":
    main()
