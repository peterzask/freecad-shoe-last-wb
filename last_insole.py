import math
import copy
import FreeCAD as App
import FreeCADGui
import Part
import Draft
import numpy as np
import traceback
import inspect
from dataclasses import dataclass
import importlib
import helper_funcs as hf
#import shape_params as sp
importlib.reload(hf)

print(f"+++++++++++++++Line({inspect.currentframe().f_lineno}) File:({__file__})+++++++++++++++++++")


@dataclass
class foot_c:
    foot_len: float = 0.0
    joint: float = 0.0
    waist: float = 0.0
    instep: float = 0.0
    h_instep: float = 0.0
    heel: float = 0.0  #heel girth
    heel_height: float = 0.0
    ankle:       float = 0.0
    toe_space:   float = 15.0
    toe_spring: float = 20.0
    def __init__(self, foot_len, joint, waist, instep,
                 h_instep, heel, heel_height, ankle, toe_space=15.0):
        self.foot_len = foot_len
        self.joint = joint
        self.waist = waist
        self.instep = instep
        self.h_instep = h_instep
        self.heel = heel
        self.heel_height = heel_height
        self.ankle = ankle
        self.toe_space = toe_space

    def print_(self):
        print("foot_c\n",
              "foot_len    (%10.4f) (%10.4f)\n"%(self.foot_len,self.foot_len/25.4),
              "joint       (%10.4f) (%10.4f)\n" %(self.joint,self.joint/25.4),
              "waist       (%10.4f) (%10.4f)\n"%(self.waist,self.waist/25.4),
              "instep      (%10.4f) (%10.4f)\n"%(self.instep,self.instep/25.4),
              "h_instep    (%10.4f) (%10.4f)\n"%(self.h_instep,self.h_instep/25.4),
              "heel        (%10.4f) (%10.4f)\n"%(self.heel,self.heel/25.4),
              "heel_height (%10.4f) (%10.4f)\n"%(self.heel_height,self.heel_height/25.4),
              "ankle       (%10.4f) (%10.4f)\n"%(self.ankle,self.ankle/25.4))


@dataclass
class insole_len_c:
    BD:   float=15.0 # Toe Allowance — overwritten from ft_meas.toe_space in __init__
    AC:   float=5.0  # 5 mm constant
    def __init__(self,  ft_meas: foot_c):
        self.AB  = ft_meas.foot_len
        self.BD  = ft_meas.toe_space
        self.CJ  = ft_meas.foot_len * 2.0 / 3.0
        self.JJ1 = ft_meas.joint / 6.0
        self.JJ2 = ft_meas.joint / 6.0 + 10.0
        self.AH  = self.AB / 5.0
        self.H1H2= ft_meas.heel / 5.0 - (ft_meas.heel_height-20.0) / 10.0
        self.AD  = self.AB + self.BD
        self.B1B2= 0.6 * (self.JJ1 + self.JJ2)
        self.H3K = 0.0
    def print_(self):
        print("insole_len_c\n",
              "\tAB    = %8.4f\n"%self.AB,
              "\tBD    = %8.4f\n"%self.BD,
              "\tAC    = %8.4f\n"%self.AC,
              "\tCJ    = %8.4f\n"%self.CJ,
              "\tJJ1   = %8.4f\n"%self.JJ1,
              "\tJJ2   = %8.4f\n"%self.JJ2,
              "\tAH    = %8.4f\n"%self.AH,
              "\tH1H2  = %8.4f\n"%self.H1H2,
              "\tH3K   = %8.4f\n"%self.H3K)


class insole_layout:
    def build(self, insole_len_c, sketch_insole:"Sketcher::Sketch_Object"):
        self.A = App.Vector(0,0,0)
        self.B = App.Vector(insole_len_c.AB,0,0)
        self.D = App.Vector(insole_len_c.AB+insole_len_c.BD,0,0)
        self.H3 = App.Vector(insole_len_c.AB/5.0,0,0)
        self.AD_line = Part.LineSegment(self.A,self.D)
        sketch_insole.addGeometry(self.AD_line,False)
        self.A_line = Part.LineSegment(App.Vector(0,-5,0),App.Vector(0,5,0)) # Visual Marker
        sketch_insole.addGeometry(self.A_line)
        self.C_line = Part.LineSegment(App.Vector(insole_len_c.AC,-5,0),App.Vector(insole_len_c.AC,5,0))
        sketch_insole.addGeometry(self.C_line)
        self.C = App.Vector(insole_len_c.AC,0,0)
        self.J = App.Vector(insole_len_c.CJ,0,0)
        self.CJ_line = Part.LineSegment(self.C,self.J)
        self.O = App.Vector(insole_len_c.CJ,-10,0)
        self.CO_line = Part.LineSegment(self.C,self.O)
        sketch_insole.addGeometry(self.CO_line,False)
        self.nCO = (self.O - self.C).normalize()
        self.perp_nCO = -self.nCO.cross(hf.nZ)
        t2 = (insole_len_c.AB) / self.nCO.x
        self.OD_line = Part.LineSegment(self.O, self.nCO*t2)
        sketch_insole.addGeometry(self.OD_line)
        # H1H2: find where |C + t*nCO| = AH
        a = 5.0; b = self.nCO.x; c = self.nCO.y; d = insole_len_c.AH
        D = b**2 + c**2
        t = -a*b/D + math.sqrt(d**2/D - a*b/D)
        self.H  = App.Vector(self.C + self.nCO*t)
        self.H2 = self.H - self.perp_nCO*(insole_len_c.H1H2/2.0)
        self.H1 = self.H + self.perp_nCO*(insole_len_c.H1H2/2.0)
        self.H1H2_line = Part.LineSegment(self.H1,self.H2)
        sketch_insole.addGeometry(self.H1H2_line)
        self.H1J_line = Part.LineSegment(self.H1,self.J)
        sketch_insole.addGeometry(self.H1J_line)
        self.nH1J1 = (App.Vector(self.J-self.H1)).normalize()
        self.perp_nH1J1 = -self.nH1J1.cross(hf.nZ)
        self.J1 = App.Vector(self.J + self.perp_nH1J1*insole_len_c.JJ1)
        self.JJ1_line = Part.LineSegment(self.J,self.J1)
        sketch_insole.addGeometry(self.JJ1_line)
        self.J2 = self.J - self.perp_nH1J1*insole_len_c.JJ2
        self.JJ2_line = Part.LineSegment(self.J, self.J2)
        sketch_insole.addGeometry(self.JJ2_line)
        sketch_insole.addGeometry(Part.LineSegment(self.J1, self.H1))
        self.H4 = self.H - self.perp_nCO*(insole_len_c.H1H2/6.0)
        self.H4J1_line = Part.LineSegment(self.H4,self.J1)
        sketch_insole.addGeometry(self.H4J1_line)
        self.H2J2_line = Part.LineSegment(self.H2,self.J2)
        sketch_insole.addGeometry(self.H2J2_line)
        self.CH1_line = Part.LineSegment(self.C,self.H1)
        sketch_insole.addGeometry(self.CH1_line)
        self.CH2_line = Part.LineSegment(self.C,self.H2)
        sketch_insole.addGeometry(self.CH2_line)
        self.B1 = App.Vector(insole_len_c.AB, insole_len_c.B1B2/2.0, 0)
        self.B2 = App.Vector(insole_len_c.AB,-insole_len_c.B1B2/2.0, 0)
        self.B1B2_line = Part.LineSegment(self.B1,self.B2)
        sketch_insole.addGeometry(self.B1B2_line)
        self.J1B1_line = Part.LineSegment(self.J1,self.B1)
        sketch_insole.addGeometry(self.J1B1_line)
        self.B1D = Part.LineSegment(self.B1,self.D)
        sketch_insole.addGeometry(self.B1D)
        self.J2B2_line = Part.LineSegment(self.J2,self.B2)
        sketch_insole.addGeometry(self.J2B2_line)
        self.B2D_line = Part.LineSegment(self.B2,self.D)
        sketch_insole.addGeometry(self.B2D_line)
        # K: intersection of J1-H4 and J-H1
        P0 = self.J1; P1 = self.H4 - self.J1
        P2 = self.J;  P3 = self.H1 - self.J
        A = np.array([[P1.x,-P3.x],[P1.y,-P3.y]], dtype=np.float64)
        b = np.array([[P2.x-P0.x],[P2.y-P0.y]], dtype=np.float64)
        t_result = np.linalg.solve(A,b)[0]
        V0 = np.array([P0.x,P0.y,P0.z])
        V1 = np.array([P1.x,P1.y,P1.z])
        self.K = App.Vector(*(V0 + V1*t_result))


    def print_(self):
        print(f"last_insole.insole_dwg.")
        hf.p_vec(self.A,"A ")
        hf.p_vec(self.B,"B ")
        hf.p_vec(self.B1,"B1")
        hf.p_vec(self.B2,"B2")
        hf.p_vec(self.C,"C ")
        hf.p_vec(self.D,"D ")
        hf.p_vec(self.J,"J ")
        hf.p_vec(self.J1,"J1")
        hf.p_vec(self.J2,"J2")
        hf.p_vec(self.K,"K ")
        hf.p_vec(self.H,"H ")
        hf.p_vec(self.H1,"H1")
        hf.p_vec(self.H2,"H2")
        hf.p_vec(self.H3,"H3")
        hf.p_vec(self.H4,"H4")
        hf.p_vec(self.O,"O " )

    def draw_vertex_circles(self, sketch_object):
        sketch_insole = sketch_object
        sketch_insole.addGeometry(Part.Circle(self.A,  hf.nZ, 2.0))
        sketch_insole.addGeometry(Part.Circle(self.B,  hf.nZ, 2.0))
        sketch_insole.addGeometry(Part.Circle(self.B1, hf.nZ, 2.0))
        sketch_insole.addGeometry(Part.Circle(self.B2, hf.nZ, 2.0))
        sketch_insole.addGeometry(Part.Circle(self.C,  hf.nZ, 2.0))
        sketch_insole.addGeometry(Part.Circle(self.D,  hf.nZ, 2.0))
        sketch_insole.addGeometry(Part.Circle(self.J,  hf.nZ, 2.0))
        sketch_insole.addGeometry(Part.Circle(self.J1, hf.nZ, 2.0))
        sketch_insole.addGeometry(Part.Circle(self.J2, hf.nZ, 2.0))
        sketch_insole.addGeometry(Part.Circle(self.H,  hf.nZ, 2.0))
        sketch_insole.addGeometry(Part.Circle(self.H1, hf.nZ, 2.0))
        sketch_insole.addGeometry(Part.Circle(self.H2, hf.nZ, 2.0))
        sketch_insole.addGeometry(Part.Circle(self.H3, hf.nZ, 2.0))
        sketch_insole.addGeometry(Part.Circle(self.H4, hf.nZ, 2.0))
        sketch_insole.addGeometry(Part.Circle(self.O,  hf.nZ, 2.0))


# --- Sketch name ---
sketch_name = "Sketch_Insole"

# Module-level handles — set by build(), used by last_profile and xs_base
doc             = None
sketch_insole   = None
ft_measurements = None
insole_lens     = None
insole_dwg      = None
outline_bc      = None   # used by xs_0, xs_1, xs_3


def build():
    global doc, sketch_insole, ft_measurements, insole_lens, insole_dwg, outline_bc
    #importlib.reload(sp)

    doc, sketch_insole = hf.Doc_Sketch(None, sketch_name)
    doc.recompute()

    import foot_meas_data as fmd
    importlib.reload(fmd)
    try:
        import meas_sheet as MS
        importlib.reload(MS)
        _raw = MS.load_foot_measurements(doc)
        MS.validate_measurements(_raw)
    except Exception as _e:
        print(f"last_insole: spreadsheet load failed ({_e}), using defaults.")
        _raw = fmd.foot_meas_raw()

    ft_measurements = foot_c(
        foot_len    = _raw.foot_len,
        joint       = _raw.joint,
        waist       = _raw.waist,
        instep      = _raw.instep,
        h_instep    = _raw.h_instep,
        heel        = _raw.heel,
        heel_height = _raw.heel_height,
        ankle       = _raw.ankle,
        toe_space   = _raw.toe_space,
    )
    #ft_measurements.print_()

    insole_lens = insole_len_c(ft_measurements)
    insole_dwg  = insole_layout()
    insole_dwg.build(insole_lens, sketch_insole)
    # outline_bc and all BSplines are built by control_curves.build() and back-assigned here
    insole_dwg.draw_vertex_circles(sketch_insole)


build()


def main():
    insole_dwg.print_()
    view = FreeCADGui.ActiveDocument.ActiveView
    if view and hasattr(view, 'viewTop'):
        view.viewTop()
        view.fitAll()
    doc.recompute()
    print("End of last_insole.py")

if __name__ == "__main__":
    main()





#dead code
    """
#    def draw_last_outline(self, sketch):
#        lateral_K = (self.J2 + self.H2 + App.Vector(0,10,0)) * 0.5
#        lateral_K.y = lateral_K.y*0.95
#        medial_K = self.K*1.0
#        medial_K.y *= 1.8
#        C0 = self.C + App.Vector(-5,0,0)
#        H1_temp = self.H1*1.0 + App.Vector(0,2,0)
#        H2_temp = self.H2*1.0 + App.Vector(0,-2,0)
#        B1_temp = self.B1*1.0 + App.Vector(1,1,0)
#        B2_temp = self.B2*1.0 + App.Vector(1,-1,0)
#        D_temp =  self.D *1.0 + App.Vector(2,0,0)
#        C2 = self.C + App.Vector(0,5+17,0)
#        C3 = self.C + App.Vector(0,-5-17,0)
#        pinky_pt = self.B2*1.0 + (self.J2-self.B2)/2 + App.Vector(0,-8,0)
#        sketch.addGeometry(Part.Circle(pinky_pt,hf.nZ,2))
#        poles = [C0, C2, H1_temp, medial_K, self.J1, B1_temp,
#                 D_temp, B2_temp, pinky_pt, self.J2, lateral_K, H2_temp, C3, C0]
#        bc = Part.BSplineCurve()
#        bc.buildFromPoles(poles, False, 2, False)
#
#        bc_medial_last_outline_poles= [C0, C2, H1_temp, medial_K, self.J1, B1_temp, D_temp]
#        self.bc_medial_last_outline = Part.BSplineCurve()
#        self.bc_medial_last_outline.buildFromPoles(bc_medial_last_outline_poles, False, 2, False)
#        sketch.addGeometry(self.bc_medial_last_outline)
#
#        bc_lateral_last_outline_poles = [D_temp, B2_temp, pinky_pt, self.J2, lateral_K, H2_temp, C3, C0]
#        self.bc_lateral_last_outline = Part.BSplineCurve()
#        self.bc_lateral_last_outline.buildFromPoles(bc_lateral_last_outline_poles, False, 2, False)
#        sketch.addGeometry(self.bc_lateral_last_outline)
#
#        return bc
        """
