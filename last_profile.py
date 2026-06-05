import math
import FreeCAD as App
import FreeCADGui
import Part
import Sketcher
import numpy as np
import traceback
import inspect
import sys
import importlib
import helper_funcs as hf
import last_insole
import shape_params as sp
import gc
from dataclasses import dataclass


print(f"+++++++++++++++Line({inspect.currentframe().f_lineno}) File:({__file__})+++++++++++++++++++++")


@dataclass
class profile_lengths_c:
    XB: float = 15.0                    # toe space
    def __init__(self, foot_c, shape_p):
        self.AH  = 1.5*25.4             # TODO: scale with HJ, see Koleff Table
        self.HJ  = 2.0 / 3.0 * foot_c.foot_len
        self.JX  = 1.0 / 3.0 * foot_c.foot_len
        self.BB1 = shape_p.toe_spring   # vertical toe spring (mm)
        self.HC5 = 81.0                 # Koleff table — doesn't scale with foot size yet
        self.HH1 = 0.9 / 2.0 * foot_c.heel
        self.HC2 = 2.0 / 5.0 * self.HC5
        self.HC1 = 1.0 / 5.0 * self.HC5
        self.C2H2 = 5
        self.HK  = 1.0 / 2.0 * self.HJ
        self.JJ1 = 1.0 / 5.0 * foot_c.joint
        self.B1B2 = 1.0 / 2.0 * self.JJ1
        self.H1E = 1.0 / 10.0 * self.HH1

    def print_(self):
        print("\nProfile Lengths:",
              "\nAH=",  self.AH,
              "\nHJ",   self.HJ,
              "\nJX",   self.JX,
              "\nBB1",  self.BB1,
              "\nHC5",  self.HC5,
              "\nHH1",  self.HH1,
              "\nHC2",  self.HC2,
              "\nC2H2", self.C2H2,
              "\nHK",   self.HK,
              "\nJJ1",  self.JJ1,
              "\nB1B2", self.B1B2,
              "\nH1E",  self.H1E)


class draw_profile_c:
    def __init__(self):
        self.heel_bc              : Part.BSplineCurve = Part.BSplineCurve()
        self.bottom_bc            : Part.BSplineCurve = Part.BSplineCurve()
        self.front_bc             : Part.BSplineCurve = Part.BSplineCurve()
        self.top_bc               : Part.BSplineCurve = Part.BSplineCurve()
        self.medial_highwater_bc  : Part.BSplineCurve = Part.BSplineCurve()
        self.lateral_highwater_bc : Part.BSplineCurve = Part.BSplineCurve()
        self.C1_profile_bc        : Part.BSplineCurve = Part.BSplineCurve()
        self.C2_profile_bc        : Part.BSplineCurve = Part.BSplineCurve()

    def build(self, PL: profile_lengths_c, sketch: "Sketcher::SketchObject"):
        # J at local origin; H to the left and up by heel raise AH
        self.J = App.Vector(0.0, 0.0, 0.0)
        self.H = App.Vector(-math.sqrt(PL.HJ**2 - PL.AH**2), PL.AH, 0.0)
        sketch.addGeometry(Part.LineSegment(self.H, self.J))
        self.X = self.J + App.Vector(PL.JX, 0.0, 0.0)
        sketch.addGeometry(Part.LineSegment(self.J, self.X))
        self.B  = self.X + App.Vector(PL.XB, 0.0, 0.0)
        self.B1 = self.B + App.Vector(0.0, PL.BB1, 0.0)
        sketch.addGeometry(Part.LineSegment(self.J, self.B1))
        sketch.addGeometry(Part.LineSegment(self.H, self.B))
        nHB = -((self.B - self.H).cross(hf.nZ)).normalize()
        self.Y1 = self.H + nHB*PL.HC5
        sketch.addGeometry(Part.LineSegment(self.H, self.Y1))
        self.C2 = self.H + nHB*(2.0/5.0*PL.HC5)
        self.H2 = self.C2 + App.Vector(-6.0, 0, 0)
        sketch.addGeometry(Part.LineSegment(self.C2, self.H2))
        self.C5  = self.Y1
        nHY1 = -((self.H - self.C5).cross(hf.nZ)).normalize()
        uHB  = (self.B - self.H).normalize()
        uHH1 = hf.rotate_vector(uHB, 37.0)
        self.H1 = self.H + uHH1*PL.HH1
        self.HH1_line = Part.LineSegment(self.H, self.H1)
        sketch.addGeometry(self.HH1_line)
        nHJ = -((self.J - self.H).cross(hf.nZ)).normalize()
        self.J1 = self.J + nHJ*PL.JJ1
        sketch.addGeometry(Part.LineSegment(self.J, self.J1))
        self.B2 = self.B1 + App.Vector(0, PL.JJ1/2.0 - 5.0, 0.0)
        sketch.addGeometry(Part.LineSegment(self.B1, self.B2))
        uJ1H1 = (self.H1 - self.J1).normalize()
        sketch.addGeometry(Part.LineSegment(self.J1, self.H1))
        self.E = self.H1 + uJ1H1*PL.H1E
        sketch.addGeometry(Part.LineSegment(self.H1, self.E))
        sketch.addGeometry(Part.LineSegment(self.B2, self.J1))
        uE140 = hf.rotate_vector(nHY1, 40)
        PtA, PtB = hf.intersect_lines(self.C5, self.C5+nHY1, self.E, self.E+uE140)
        self.C5E_intercept = PtA
        sketch.addGeometry(Part.LineSegment(self.E,   self.C5E_intercept))
        sketch.addGeometry(Part.LineSegment(self.C5,  self.C5E_intercept))
        self.Kb = (self.H + self.J)/2.0
        self.K1 = self.H + (PL.HJ+PL.JX)/5.0*(self.J-self.H).normalize()

    def compute_K(self, insole_dwg, placement: App.Placement):
        # Find K: point on profile bottom line above insole K, raised 8mm
        gvec_uHC5 = hf.xz_xy_place * (self.C5 - self.H).normalize()
        start_K = insole_dwg.K
        end_K   = start_K + gvec_uHC5 * 200
        g_H = placement.multVec(self.H)
        g_B = placement.multVec(self.B)
        K_a, K_b = hf.intersect_lines(start_K, end_K, g_H, g_B)
        local_K = placement.inverse().multVec(K_b)
        local_K.y += 8
        local_K.z  = 0
        self.K = local_K

    def draw_outline(self, sketch):
        self.heel_bc.buildFromPoles([self.C5, self.H2+App.Vector(-5,0,0), self.H],
                               False, 2, True)
        sketch.addGeometry(self.heel_bc)
        self.bottom_bc.buildFromPoles([self.H, self.K1, self.K,
                                  self.J+App.Vector(0,-10,0), self.B1],
                                 False, 2, True)
        sketch.addGeometry(self.bottom_bc)
        # TODO: ratiometric offsets (see comments)
        self.front_bc.buildFromPoles([self.B1, self.B2+App.Vector(5,5,0),
                                 self.J1+App.Vector(0,-10,0), self.H1, self.E],
                                False, 2, False)
        sketch.addGeometry(self.front_bc)
        self.top_bc.buildFromPoles([self.E, self.C5E_intercept, self.C5],
                              False, 2, False)
        sketch.addGeometry(self.top_bc)

        self.front_top_bc = Part.BSplineCurve()
        self.front_top_bc.buildFromPoles([self.B1, self.B2+App.Vector(5,5,0),
                                 self.J1+App.Vector(0,-10,0), self.H1, self.E,
                                 self.E, self.C5E_intercept, self.C5E_intercept, self.C5],
                                False, 2, False)
        sketch.addGeometry(self.front_top_bc)

    def _build_highwater_poles(self, pct_instep: float, pct_joint: float):
        Pa = self.K
        Pb = self.J1 + (self.H1 - self.J1) * 2.0/3.0
        return [self.H2,
                self.H2 + App.Vector(60, -10, 0),
                Pa + (Pb - Pa) * pct_instep,
                self.J + (self.J1 - self.J) * pct_joint,
                self.B1 + (self.B2 - self.B1) * 2.0/3.0]

    def draw_highwater_medial(self, sketch, shape_p):
        self.medial_highwater_bc = Part.BSplineCurve()
        self.medial_highwater_bc.buildFromPoles(
            self._build_highwater_poles(shape_p.hw_med_pct_instep,
                                        shape_p.hw_med_pct_joint),
            False, 3, False)

    def draw_highwater_lateral(self, sketch, shape_p):
        self.lateral_highwater_bc = Part.BSplineCurve()
        self.lateral_highwater_bc.buildFromPoles(
            self._build_highwater_poles(shape_p.hw_lat_pct_instep,
                                        shape_p.hw_lat_pct_joint),
            False, 3, False)

    def draw_crown_profiles(self, sketch, shape_p):
        degree = 2
        Pa = self.K
        Pb = self.J1 + (self.H1 - self.J1) * 2.0/3.0
        toe_anchor = self.B1 + (self.B2 - self.B1) * 2.0/3.0

        poles_c1 = [
            toe_anchor,
            self.J  + (self.J1  - self.J)  * shape_p.crown_med_pct_joint,
            Pa      + (Pb       - Pa)       * shape_p.crown_med_pct_instep,
            self.E,
            self.C5,
        ]
        self.C1_profile_bc.buildFromPoles(poles_c1, False, degree, False)
        sketch.addGeometry(self.C1_profile_bc)

        poles_c2 = [
            toe_anchor,
            self.J  + (self.J1  - self.J)  * shape_p.crown_lat_pct_joint,
            Pa      + (Pb       - Pa)       * shape_p.crown_lat_pct_instep,
            self.E,
            self.C5,
        ]
        self.C2_profile_bc.buildFromPoles(poles_c2, False, degree, False)
        sketch.addGeometry(self.C2_profile_bc)

    def draw_circles(self, sketch: "Sketcher::SketchObject"):
        sketch.addGeometry(Part.Circle(self.H,             hf.nZ, 2.0))
        sketch.addGeometry(Part.Circle(self.K1,            hf.nZ, 2.0))
        sketch.addGeometry(Part.Circle(self.K,             hf.nZ, 2.0))
        sketch.addGeometry(Part.Circle(self.Kb,            hf.nZ, 2.0))
        sketch.addGeometry(Part.Circle(self.J,             hf.nZ, 2.0))
        sketch.addGeometry(Part.Circle(self.B1,            hf.nZ, 2.0))
        sketch.addGeometry(Part.Circle(self.B2,            hf.nZ, 2.0))
        sketch.addGeometry(Part.Circle(self.J1,            hf.nZ, 2.0))
        sketch.addGeometry(Part.Circle(self.H1,            hf.nZ, 2.0))
        sketch.addGeometry(Part.Circle(self.E,             hf.nZ, 2.0))
        sketch.addGeometry(Part.Circle(self.C5E_intercept, hf.nZ, 2.0))
        sketch.addGeometry(Part.Circle(self.C5,            hf.nZ, 2.0))
        sketch.addGeometry(Part.Circle(self.H2,            hf.nZ, 2.0))


def build_xs_plane_pi(plane_name:str, plane_place: App.Placement, display_on: bool = False):
    if doc.getObject(plane_name):
        doc.removeObject(plane_name)
        gc.collect()
        doc.recompute()
    if display_on == False: return
    width  = 100
    height = 83
    plane_shape = Part.makePlane(width, height, App.Vector(-width/2,0,0), hf.nZ, hf.nX)
    plane_object = doc.addObject("Part::Feature", plane_name)
    plane_object.Shape = plane_shape
    plane_object.Placement = plane_place*hf.yz_xy_place
    print(f"Added plane {plane_name}")
    doc.recompute()


# Module-level handles — set by build(), used by xs_base
doc           = None
sketch_profile = None
p_lens        = None
profile_dwg   = None


def build():
    global doc, sketch_profile, p_lens, profile_dwg
    importlib.reload(sp)

    ft_measurements = last_insole.ft_measurements
    ft_measurements.print_()

    doc_name    = "ScriptModel"
    sketch_name = "Sketch_Profile"
    doc, sketch_profile = hf.Doc_Sketch(doc_name, sketch_name)

    p_lens = profile_lengths_c(ft_measurements, sp.shape_params)
    p_lens.print_()
    profile_dwg = draw_profile_c()
    profile_dwg.build(p_lens, sketch_profile)

    sketch_profile.Placement = App.Placement(
        App.Vector(last_insole.insole_lens.CJ, 0, 0),
        hf.xz_xy_place.Rotation)

    profile_dwg.compute_K(last_insole.insole_dwg, sketch_profile.Placement)

    profile_dwg.draw_outline(sketch_profile)
    profile_dwg.draw_highwater_medial(sketch_profile, sp.shape_params)
    profile_dwg.draw_highwater_lateral(sketch_profile, sp.shape_params)
    profile_dwg.draw_crown_profiles(sketch_profile, sp.shape_params)
    profile_dwg.draw_circles(sketch_profile)


build()


def main():
    print("In last_profile_main")

if __name__ == "__main__":
    main()
