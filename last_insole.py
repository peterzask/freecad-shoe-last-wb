
#!/usr/bin/python3
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
importlib.reload(hf)

print(f"+++++++++++++++Line({inspect.currentframe().f_lineno}) File:({__file__})+++++++++++++++++++")


@dataclass
class foot_c:
    fl: float = 0.0
    joint: float = 0.0
    waist: float = 0.0
    instep: float = 0.0
    h_instep: float = 0.0
    heel: float = 0.0  #heel girth
    heel_height: float = 0.0
    ankle: float = 0.0
    def __init__(self, fl, joint, waist, instep, 
                 h_instep, heel, heel_height, ankle):
        self.fl = fl
        self.joint = joint
        self.waist = waist
        self.instep = instep
        self.h_instep = h_instep
        self.heel = heel
        self.heel_height = heel_height
        self.ankle = ankle

    def print_(self):
        print("foot_c\n",
              "fl       (%10.4f)\n"%self.fl,
              "joint    (%10.4f)\n"%self.joint,
              "waist    (%10.4f)\n"%self.waist,
              "instep   (%10.4f)\n"%self.instep,
              "h_instep (%10.4f)\n"%self.h_instep,
              "heel     (%10.4f)\n"%self.heel,
              "heel_height (%10.4f)\n"%self.heel_height,
              "ankle    (%10.4f)\n"%self.ankle)


@dataclass
class insole_len_c:
    BD:   float=15.0 # Toe Allowance, default = 15mm
    AC:   float=5.0  # 5 mm constant
    def __init__(self,  ft_meas: foot_c):
        print(ft_meas)
        print("Here")
        print(ft_meas.fl)
        self.AB = ft_meas.fl
        self.CJ = ft_meas.fl * 2.0 / 3.0
        self.JJ1 = ft_meas.joint / 6.0
        self.JJ2 = ft_meas.joint / 6.0 + 10.0
        self.AH = self.AB / 5.0
        self.H1H2 = ft_meas.heel / 5.0 - ft_meas.heel_height / 10.0
        self.AD = self.AB + self.BD
        self.B1B2 = 0.6 * (self.JJ1 + self.JJ2)
        self.H3K = 0.0
    def print_(self):
        print("insole_len_c\n",
              "AB       = %10.4f\n"%self.AB,
              "BD       = %10.4f\n"%self.BD,
              "AC       = %10.4f\n"%self.AC,
              "CJ       = %10.4f\n"%self.CJ,
              "JJ1      = %10.4f\n"%self.JJ1,
              "JJ2      = %10.4f\n"%self.JJ2,
              "AH      = %10.4f\n"%self.AH,
              "H1H2    = %10.4f\n"%self.H1H2,
              "H3K     = %10.4f\n"%self.H3K)


@dataclass
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
        #sketch_insole.addGeometry(Part.Circle(self.K, hf.nZ, 2.0))

    def draw_last_outline(self, sketch):
        lateral_K = (self.J2 + self.H2 + App.Vector(0,10,0)) * 0.5
        lateral_K.y = lateral_K.y*0.95
        medial_K = self.K*1.0
        medial_K.y *= 1.8
        C0 = self.C + App.Vector(-5,0,0)  # change naming to follow right hand rule thumb up in z-direction
        H1_temp = self.H1*1.0 + App.Vector(0,2,0)
        H2_temp = self.H2*1.0 + App.Vector(0,-2,0)
        B1_temp = self.B1*1.0 + App.Vector(1,1,0)
        B2_temp = self.B2*1.0 + App.Vector(1,-1,0)
        D_temp =  self.D *1.0 + App.Vector(2,0,0)
        C2 = self.C + App.Vector(0,5+17,0)  # change to follow right hand rule thumb up in z-direction
        C3 = self.C + App.Vector(0,-5-17,0)
        pinky_pt = self.B2*1.0 + (self.J2-self.B2)/2 + App.Vector(0,-8,0)
        sketch.addGeometry(Part.Circle(pinky_pt,hf.nZ,2))
        poles = [C0, C2, H1_temp, medial_K, self.J1, B1_temp,
                 D_temp, B2_temp, pinky_pt, self.J2, lateral_K, H2_temp, C3, C0]
        bc = Part.BSplineCurve()
        bc.buildFromPoles(poles, False, 2, False)
        #sketch.addGeometry(bc)
        # bc is by default in global coordinates 

        bc_medial_last_outline_poles= [C0, C2, H1_temp, medial_K, self.J1, B1_temp,
                 D_temp] #, B2_temp, pinky_pt, self.J2, lateral_K, H2_temp, C3, C0]
        self.bc_medial_last_outline = Part.BSplineCurve()
        self.bc_medial_last_outline.buildFromPoles(bc_medial_last_outline_poles, False, 2, False)
        sketch.addGeometry(self.bc_medial_last_outline)

        bc_lateral_last_outline_poles = [#C0, C2, H1_temp, medial_K, self.J1, B1_temp,
                 D_temp, B2_temp, pinky_pt, self.J2, lateral_K, H2_temp, C3, C0]
        self.bc_lateral_last_outline = Part.BSplineCurve()
        self.bc_lateral_last_outline.buildFromPoles(bc_lateral_last_outline_poles, False, 2, False)
        sketch.addGeometry(self.bc_lateral_last_outline)
        

        return bc

    def draw_insole_outline(self, sketch, crown_fraction=0.3):
        extra_point_K = (self.J2 + self.H2 + App.Vector(0,20,0)) * 0.5
        K2 = self.K + App.Vector(0,-5,0)
        C2 = self.C + App.Vector(5,5+15,0)
        C3 = self.C + App.Vector(5,-5-15,0)
        poles = [self.C, C2, self.H1, K2, self.J1, self.B1, self.D ,
                 self.B2, self.J2, extra_point_K, self.H2, C3, self.C]
        bc = Part.BSplineCurve()
        bc.buildFromPoles(poles, False, 2, False)
        sketch.addGeometry(bc)

        poles_medial = [self.C, C2, self.H1, K2, self.J1, self.B1, self.D]
        self.insole_bc_medial = Part.BSplineCurve()
        self.insole_bc_medial.buildFromPoles(poles_medial, False, 2, False)
        sketch.addGeometry(self.insole_bc_medial)

        poles_lateral = [self.D,self.B2, self.J2, extra_point_K, self.H2, C3, self.C]
        self.insole_bc_lateral = Part.BSplineCurve()
        self.insole_bc_lateral.buildFromPoles(poles_lateral, False, 2, False)
        sketch.addGeometry(self.insole_bc_lateral)

        # C1/C2 crown contour curves: same pole x-positions as insole outline,
        # y-values scaled by crown_fraction.  Tune crown_fraction at the call site.
        # Calculate distance x from C that last crown H should be at,
        # the problem is it's a more complicated calcution to be updated
        # after seeing if this works
        cosd = math.cos(37.0*math.pi/180.0)
        insole_Crown = App.Vector(ft_measurements.heel*.9/2*cosd-10,0,0) 
        _ic = insole_Crown
        print(f"heel*.45 = {insole_Crown.x}")
        sketch.addGeometry(Part.Circle(insole_Crown,hf.nZ,4))
        #C1 is medial side, points are heel to toe
        #_cf = crown_fraction
        _cf = 0.7 #crown_fraction
        poles_c1 = [
            App.Vector(self.C.x,         0,                      0),
            App.Vector(C2.x,              12.5,             0),
#            App.Vector(C2.x,             C2.y * _cf,             0),
            App.Vector(self.H1.x,         12.5,        0),
#            App.Vector(self.H1.x,        self.H1.y * _cf,        0),
#            App.Vector(K2.x,             K2.y  * _cf,            0),
            App.Vector(_ic.x,             12.5  ,            0),
            #App.Vector(_ic.x,             0  ,            0),
            #App.Vector(K2.x,             12.5  ,            0),
            #App.Vector(K2.x,             0  ,            0),
            App.Vector(self.J1.x-20,        self.J1.y*_cf ,        0),
            App.Vector(self.J1.x+10,        self.J1.y*_cf ,        0),
            App.Vector(self.B1.x,        self.B1.y*_cf  ,        0),
            App.Vector(self.D.x,         0,                      0),
        ]
        #for q in poles_c1:
        #    sketch.addGeometry(Part.Circle(q+App.Vector(0,00,0),hf.nZ,4))
        self.C1_insole_medial = Part.BSplineCurve()
        self.C1_insole_medial.buildFromPoles(poles_c1, False, 2, False)
        sketch.addGeometry(self.C1_insole_medial)
        #C2 is lateral side, points are toe to heel
        _cf = 0.5
        poles_c2 = [
#            App.Vector(self.D.x,         0,                      0),
            App.Vector(self.D.x,         0,                      0),
#            App.Vector(self.B2.x,        self.B2.y * _cf,        0),
            App.Vector(self.B2.x,        self.B2.y*_cf,        0),
#            App.Vector(self.J2.x,        self.J2.y * _cf,        0),
            App.Vector(self.J2.x+10,        self.J2.y *_cf,        0),
#            App.Vector(extra_point_K.x,  extra_point_K.y * _cf,  0),
#new pole
            App.Vector(self.J2.x-10,self.J2.y*_cf,0),
            #App.Vector(_temp.x,_temp.y,        0),
#end new pole
#            App.Vector(extra_point_K.x,  0,  0),
            #App.Vector(_ic.x,  0,  0),
#            App.Vector(extra_point_K.x,  -12.5,  0),
            App.Vector(_ic.x,  -12.5,  0),
            #App.Vector(self.H2.x,        self.H2.y * _cf,        0),
            App.Vector(self.H2.x,        -12.5,        0),
            #App.Vector(C3.x,             C3.y * _cf,             0),
            App.Vector(C3.x,             -12.5,             0),
            App.Vector(self.C.x,         0,                      0),
        ]
        #sketch.addGeometry(Part.Circle(extra_point_K,hf.nZ,8))
        #sketch.addGeometry(Part.Circle(_temp,hf.nZ,18))
        #for q in poles_c1:
        #    sketch.addGeometry(Part.Circle(q+App.Vector(0,-30,0),hf.nZ,4))
        self.C2_insole_lateral = Part.BSplineCurve()
        self.C2_insole_lateral.buildFromPoles(poles_c2, False, 2, False)
        sketch.addGeometry(self.C2_insole_lateral)

        return bc

    def print_(self):
        """      one = False
        if(False):
            print("\nA",self.A,
            "\nB",self.B,
            "\nB1",self.B1,
            "\nB2",self.B2,
            "\nC",self.C,
            "\nD",self.D,
            "\nJ",self.J,
            "\nJ1",self.J1,
            "\nJ2",self.J2,
            "\nK",self.K,
            "\nH",self.H,
            "\nH1",self.H1,
            "\nH2",self.H2,
            "\nH3",self.H3,
            "\nH4",self.H4,
            "\nO" ,self.O)
            else:"""
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


# --- Document and sketch ---
doc_name = "ScriptModel"
sketch_name = "Sketch_Insole"
doc, sketch_insole = hf.Doc_Sketch(doc_name, sketch_name)
doc.recompute()

# --- Measurements ---
ft_measurements = foot_c(fl=(11+1/8)*25.4,
            joint=25.4*11,
            waist=25.4*9.5,
            instep=25.4*9.75,
            h_instep=25.4*10.5,
            heel=25.4*(13.5-.5),
            heel_height=25.4*1.5,
            ankle=25.4*10)
#ft_measurements.print_()


# --- Build and draw ---
insole_lens = insole_len_c(ft_measurements)
#insole_lens.print_()
insole_dwg = insole_layout()
insole_dwg.build(insole_lens, sketch_insole)
outline_bc =insole_dwg.draw_insole_outline(sketch_insole)
last_outline_bc = insole_dwg.draw_last_outline(sketch_insole)
insole_dwg.draw_vertex_circles(sketch_insole)
#insole_dwg.print_()
#sketch_insole.addGeometry(Part.Circle(App.Vector(0,0,0),hf.nZ,5))
#print(f"insole_dwg.C ({insole_dwg.C})")

view = FreeCADGui.ActiveDocument.ActiveView
view.viewTop()
view.fitAll()
doc.recompute()





def main():

    insole_dwg.print_(); 
    
    print("End of last_insole.py")
if __name__ == "__main__":
    main()







#dead code

    # Parameters: (String, FontPath, Height, Tracking)
    #shapeString= Draft.makeShapeString("Hello World", 
    #                                   "/usr/share/fonts/truetype//dejavu//DejaVuSans.ttf",
    #                                   5.0)
    #
    #extrude_obj = App.ActiveDocument.addObject("Part::Feature", "ExtrudeText")
    #print(f"type shapeString {type(shapeString)}")
    #print(f"type extrude_obj {type(extrude_obj)}")
    #toShape(shapeString)
    #
    ##extrude_obj.Base = shapeString
    ##extrude_obj.Dir = App.Vector(0,0,5)
    ##extrude_obj.Solid = True
    #App.ActiveDocument.recompute()
    """
        poles_c2 = [
#            App.Vector(self.D.x,         0,                      0),
            App.Vector(self.D.x-5,         0,                      0),
#            App.Vector(self.B2.x,        self.B2.y * _cf,        0),
            App.Vector(self.B2.x,        self.B2.y,        0),
#            App.Vector(self.J2.x,        self.J2.y * _cf,        0),
            App.Vector(self.J2.x,        self.J2.y ,        0),
#            App.Vector(extra_point_K.x,  extra_point_K.y * _cf,  0),
#new pole
            #App.Vector(_temp.x,_temp.y,        0),
#end new pole
            App.Vector(extra_point_K.x,  0,  0),
            App.Vector(extra_point_K.x,  -12.5,  0),
            #App.Vector(self.H2.x,        self.H2.y * _cf,        0),
            App.Vector(self.H2.x,        -12.5,        0),
            #App.Vector(C3.x,             C3.y * _cf,             0),
            App.Vector(C3.x,             -12.5,             0),
            App.Vector(self.C.x,         0,                      0),
    """
        #dead code
        #def temp_a(): #> AppVector()
        #    _l_uJ2exK = extra_point_K-self.J2 
        #    return self.J2 - _l_uJ2exK.multiply(0.5)
        #_temp=temp_a()
        #_temp = App.Vector(self.J2.x,self.J2.y*.5,0)