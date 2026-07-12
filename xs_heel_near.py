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
        self.CC1 = xs_base.xs_heel_near.CC1
        self.CC2 = xs_base.xs_heel_near.CC2
        self.HC1 = xs_base.xs_heel_near.HC1
        self.HC2 = xs_base.xs_heel_near.HC2

        # T ring: axial position + height from bc_3d_heel at t=0.30 (same t as
        # xs_heel_near_row in xs_base), lateral from last outline at that x.
        # T1/T2 sit OFF the xs_heel_near plane, tracing the heel cup arc.
        # Axial position (x): bc_3d_heel at t=0.30 places T off-plane toward the heel cup.
        # Height (z): highwater level from xs_heights — bc_3d_heel.value(0.30).z is
        #             near-crown height (~55mm), far above the T ring's correct height.
        # Lateral (y): last outline at that x.
        _p_m = xs_base.bc_3d_heel.value(0.30)  # x=axial position, z ignored for T height
        _HT  = xs_base.xs_heel_near.HT1
        # World z at highwater height: origin + HT1 along gvec_uHC5.
        _z_hw = (xs_base.xs_heel_near_placement.Base
                 + xs_base.gvec_uHC5 * _HT).z
        print(f"xs_heel_near bc_3d_heel.value(0.30).x={_p_m.x:.2f}  HT1={_HT:.2f}  z_hw={_z_hw:.2f}")
        try:
            _TT1 = hf.get_bspline_plane_intersection_new(
                control_curves.bc_medial_last_outline,
                App.Vector(_p_m.x, 0, 0), hf.nX)[0].y
        except IndexError:
            print(f"xs_heel_near T1 outline fallback at x={_p_m.x:.2f}")
            _TT1 = xs_base.xs_heel_near.HH1
        try:
            _TT2 = hf.get_bspline_plane_intersection_new(
                control_curves.bc_lateral_last_outline,
                App.Vector(_p_m.x, 0, 0), hf.nX)[0].y
        except IndexError:
            print(f"xs_heel_near T2 outline fallback at x={_p_m.x:.2f}")
            _TT2 = xs_base.xs_heel_near.HH2
        # World-space T positions — x off-plane (on heel cup), y from outline, z at highwater.
        # row_world() injects these directly; pl_hn.multVec() is NOT applied to them.
        self.T1_world = App.Vector(_p_m.x, _TT1, _z_hw)
        self.T2_world = App.Vector(_p_m.x, _TT2, _z_hw)
        print(f"xs_heel_near T1_world={self.T1_world}  T2_world={self.T2_world}")

    def build(self):
        sc    = xs_base.xs_heel_near
        _H_y  = (sc.H  - xs_base.xs_heel_near_placement.Base).dot(xs_base.gvec_uHC5)
        _H3_y = (sc.H3 - xs_base.xs_heel_near_placement.Base).dot(xs_base.gvec_uHC5)
        self.H  = App.Vector(0,       _H_y,  0)
        self.H1 = App.Vector( sc.HH1, _H_y,  0)
        self.H2 = App.Vector( sc.HH2, _H_y,  0)
        self.H3 = App.Vector(0,       _H3_y, 0)
        # T1/T2 for sketch display only (in-plane); actual surface positions are T1_world/T2_world.
        self.T1 = App.Vector( sc.TT1, sc.HT1, 0)
        self.T2 = App.Vector( sc.TT2, sc.HT2, 0)
        t       = sc.TT1 / (sc.TT1 - sc.TT2)
        self.T  = App.Vector(0, sc.HT1 + t * (sc.HT2 - sc.HT1), 0)
        self.C  = App.Vector(0,         self.HC,  0)
        self.C1 = App.Vector( self.CC1, self.HC1, 0)
        self.C2 = App.Vector(-self.CC2, self.HC2, 0)
        self.ctrl = xs_base.xs_ctrl_pts_c(
            H3=self.H3, H=self.H,  H1=self.H1, H2=self.H2,
            T=self.T,   T1=self.T1, T2=self.T2,
            C=self.C,   C1=self.C1, C2=self.C2)
        self.control_points = self.ctrl.control_points()

    def row_world(self, pl_hn, crisp_sole=False):
        """Row in world space. T1/T2 are world positions off the xs_heel_near plane;
        all other points are transformed from local sketch space by pl_hn."""
        pts = [pl_hn.multVec(pv) for pv in self.ctrl.control_points(crisp_sole)]
        t1_idx, t2_idx = (4, 8) if crisp_sole else (3, 7)
        pts[t1_idx] = self.T1_world
        pts[t2_idx] = self.T2_world
        return pts

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
