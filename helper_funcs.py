import math
import inspect
import FreeCAD as App
import Part 
import numpy as np
# This file does not import any 
# local files

# vim not working: ctrl-shift-p, Developer: Reload Window

# naming conventions, nomenclature notes
# coordinate point notation:
#   g_ - global coordinate
#   u  - unit vector
#   l_ - local coordinate in FreeCAD Sketchs,
#         FreeCAD sketches are alwasy in an x-y coordinate system, 
#         and get changed to global 3d systme location 
# by Placement Matrices (Transformation Matrix 
# the rotates then translates) sketch to plane in 3d
# Rotation matrix naming, follows John J. Craig's in "~Intro to Robotics ..."
# R_to_from    one of the App.Rotation me (start_vec, end_vec)
#                      or App.Rotation(from,to)
#
#    {to} |zt         R_to_from                {from}|zf
#         |          [xt*xf  xt*yf  xt*zf            |  /yf
#         |           yt*xf  yt*yf  yt*zf            | /
#         |           zt*xf  zt*yf  zt*zf]           |/
#        / \                                          \
#       /   \         R_to_from                        \
#   xt /     \ yt     [0    -1   0                      \xf
#                      1     0   0            
#                      0     0   1]          a dot b shown as a*b
#   The columns R_to_from are from's axis
#   in to's coordinates
#   The rows of R_to_from are to's axis
#   in from's coordinates
#   For Pfrom = (100,0,-50) 
# P_to = R_to_from * P_from = (0,-100,-50)
#   Conversely, The rows of R_to_from are
#   to's coordinate axis in from's coordinates.
#   For, P_to = (1,1,0), P_from = transpose(P_to_from)*P_to = (1,-1,0)

xz_xy_place = App.Placement(App.Vector(0,0,0), App.Rotation(App.Vector(1,0,0),90))
#xz_xy_place = App.Placement(App.Vector(0,0, 0), 
#              App.Rotation(App.Vector(1, 0, 0), #Treated as Column vectors of the rotation matrix, so this is the X axis of the new frame
#                           App.Vector(0, 0, 1),
#                           App.Vector(0, -1, 0)))

eyeRot = App.Rotation(0,0,0)

yz_xy_place = App.Placement(App.Vector(0,0,0),App.Rotation(App.Vector(1,1,1),120))
nX = App.Vector(1.0,0.0,0.0)    
nY = App.Vector(0.0,1.0,0.0)    
nZ = App.Vector(0.0,0.0,1.0)  


print(f"++++++++++Line({inspect.currentframe().f_lineno}) File:({__file__})+++++++++++")
def rotate_vector(A: App.Vector, degrees:float):
    theta = math.pi*degrees/180.0
    ct = math.cos(theta)
    st = math.sin(theta)
    new_x = ct*A.x - st*A.y
    new_y = st*A.x + ct*A.y
    return App.Vector(new_x,new_y,A.z)
    

def Doc_Sketch(doc_or_name, sketch_name: str):
    if doc_or_name is None:
        doc = App.ActiveDocument
        if doc is None:
            raise RuntimeError("Doc_Sketch: no active FreeCAD document.")
    elif isinstance(doc_or_name, str):
        if doc_or_name in App.listDocuments():
            doc = App.getDocument(doc_or_name)
        else:
            print(f"'{doc_or_name}' was not found, opening new one.")
            doc = App.newDocument(doc_or_name)
            doc.UndoMode = 0
    else:
        doc = doc_or_name  # already a document object
    list_of_sketches = doc.findObjects("Sketcher::SketchObject")
    #print("\nList of sketches:\n",list_of_sketches)
    internal_sketch_names = [sk.Name for sk in list_of_sketches]
    display_labels = [sk.Label for sk in list_of_sketches]
    #print(f"Intrnal Names: {internal_sketch_names}")
    #print(f"Display Labels: {display_labels}")   
    #Reuse sketch_name if it exist (clear it), open new one otherwise.
    if sketch_name in internal_sketch_names: 
        sketch = doc.getObject(sketch_name) #"Sketcher::SketchObject",sketch_name)
        sketch.deleteAllGeometry()
        #print("\nSketch exist already, clearing and reusing\n")
    else:
        sketch = doc.addObject("Sketcher::SketchObject", sketch_name) 
        #print("\nSketch opend new\n")
    return doc,sketch

#usage:  (Not tested) 
# edges = []
# edges.append(bspline.toShape())
# arc_length_edges(edges)
def arc_length_edges(edge_list = []):
    lSum = 0
    #edges = FreeCADGui.Selection.getSelectionEx()[0].SubObjects
    #for edge in edges:
    for edge in edge_list:
      l = edge.Length
      lSum = lSum + l
    dia = lSum/math.pi
    print('Total: '+str(lSum))
    print('Equivalent circle diameter: '+str(dia))
    
def deBoor_avg(P:"list[FreeCAD.Vector]", degree:int) -> "tuple[list[float], list[float]]":
    # Knot vector by de Boor averaging (Piegl & Tiller eqn 9.8).
    # Returns (u, t):
    #   t — chord-length parameters, t[0]=0, t[n-1]=1
    #   u — flat clamped knot vector, length n+p+1
    #         leading/trailing p+1 zeros/ones; interior knots are always
    #         distinct for non-degenerate input (no repeated interior mults)
    # NOTE: FreeCAD's buildFromPolesMultsKnots requires distinct knots +
    # multiplicities, not a flat vector.  Convert at the call site:
    #   from collections import Counter
    #   counts = Counter(u); knots = sorted(counts)
    #   mults  = [counts[k] for k in knots]
    #   → end mults = p+1, all interior mults = 1 for non-degenerate input
    n = len(P)
    p = degree
    m = n + p + 1   # total knot count (indices 0..m-1)

    # Chord-length parameterization: t[0]=0, t[n-1]=1
    t = [0.0] * n
    plast = P[0]
    for j in range(1, n):
        t[j] = t[j-1] + (P[j] - plast).Length
        plast = P[j]
    total = t[n-1]
    if total == 0.0:
        raise ValueError("deBoor_avg: all control points are coincident")
    for j in range(n):
        t[j] /= total

    # de Boor averaging
    # u[0..p] = 0,  u[m-p-1..m-1] = 1
    # u[j+p]  = (1/p) * sum(t[i] for i=j..j+p-1),  j=1..n-p-1
    # All m slots are filled by the three ranges below; 0.0 init is not a sentinel.
    u = [0.0] * m
    for j in range(1, n - p):       # interior knots u[p+1..n-1]
        u[j + p] = sum(t[i] for i in range(j, j + p)) / p
    for j in range(m - p - 1, m):   # trailing p+1 ones
        u[j] = 1.0
    return u, t
    

# Print 3x3 matrix
def print_3x3_matrix(m=App.Rotation):
    print("Matrix Print")
    for i in range(0,3):
        print(f"{m.row(i).x:8.5f}, {m.row(i).y:8.5f}, {m.row(i).z:8.5f}") 
         
# Print 4x4 matrix    
def print_4x4_matrix(m=App.Rotation,optional_str=None):
    print(f"\n\t\t\t{optional_str}\n\t\t\t{m.A11:8.4f}, {m.A12:8.4f}, {m.A13:8.4f}, {m.A14:8.4f}\n\t\t\t{m.A21:8.4f}, {m.A22:8.4f}, {m.A23:8.4f}, {m.A24:8.4f}",
        f"\n\t\t\t{m.A31:8.4f}, {m.A32:8.4f}, {m.A33:8.4f}, {m.A34:8.4f}\n\t\t\t{m.A41:8.4f}, {m.A42:8.4f}, {m.A43:8.4f}, {m.A44:8.4f}")

def p_vec(v:App.Vector,name:str=None):
    #print(f"{name}\n{v.x:12.4f}\n{v.y:12.4f}\n{v.z:12.4f}\n")
    print(f"{name:10}  ({v.x:10.4f},{v.y:10.4f},{v.z:10.4f})")
    return

def print_placement(placement: App.Rotation, name:str=None):
    print(f"\n\t\t\t{name}\n\t\t\t{m.A11:8.4f}, {m.A12:8.4f}, {m.A13:8.4f}, {m.A14:8.4f}\n\t\t\t{m.A21:8.4f}, {m.A22:8.4f}, {m.A23:8.4f}, {m.A24:8.4f}",
        f"\n\t\t\t{m.A31:8.4f}, {m.A32:8.4f}, {m.A33:8.4f}, {m.A34:8.4f}\n\t\t\t{m.A41:8.4f}, {m.A42:8.4f}, {m.A43:8.4f}, {m.A44:8.4f}")

    #print(f"{name} Placement:\nBase: {placement.Base}\nRotation: {placement.Rotation}")
    return
    
    
def pt_intersect_line(p:App.Vector, p0:App.Vector, p1:App.Vector):
    t = (p-p0).dot(p1-p0) / (p1-p0).dot(p1-p0)
    P = (1-t)*p+t*p0
    return t,P
 
# Plane model: 0  =  u.dot(P_projected) -d
def point_on_plane(uPlane: App.Vector, d: float, Point: App.Vector):
    L = uPlane.Length   # make sure it's a unit vector
    u= uPlane / L
    D= d #/ L           # this should be trun if L = 1
    P_projected = Point - (u.dot(Point)-D)*u
    return P_projected



def line_intersect_plane(uPlane: App.Vector, d: float, P0: App.Vector, P1: App.Vector):
        a = uPlane.dot(P0) - d
        b = uPlane.dot(P1) - d
        if(np.abs(a-b) < np.abs(a+b)):
            raise Exception("In: line_intersect_plane, points on same side of plane.") 
        t = np.abs(a)/np.abs(a-b) 
        P = P0 + (P1 - P0)*t
        return P 
         
def intersect_lines(p0: App.Vector, p1: App.Vector, p2: App.Vector, p3: App.Vector):
    # Pa(t) = p0 + t*(p1-p0)   == Pb(s) = p2 + s*(p3-p2)
    #       3x2             2x1       3x1
    # [(p1-p0) , -(p3-p2)] [t,s]' = [(p2-p0)]
    # Ax=b, x = pinv(A)*b
    A = np.array([[(p1.x-p0.x),-(p3.x-p2.x)],
                  [(p1.y-p0.y),-(p3.y-p2.y)],
                  [(p1.z-p0.z),-(p3.z-p2.z)]])
    b = np.array([[p2.x-p0.x],[p2.y-p0.y],[p2.z-p0.z]])
    x = np.linalg.pinv(A)@b
    t = x[0].item()
    s = x[1].item()
    PtA = (p0 + t*(p1-p0))
    PtB = (p2 + s*(p3-p2))
    return PtA,PtB


# Example usage:
#   spline = doc.getObject("MyBSpline")
#   pts = get_bspline_plane_intersection_new(spline, App.Vector(0,0,0), App.Vector(0,0,1))
def get_bspline_plane_intersection_new(
        bspline_obj:  "Part.BSplineCurve",
        plane_origin: "App.Vector",
        plane_normal: "App.Vector") -> "list[App.Vector]":
    """Intersect a BSplineCurve with an infinite plane; return intersection points as Vectors."""
    printouts_on = False
    if(printouts_on):
        print(f"++++++++++Line({inspect.currentframe().f_lineno}) File:({__file__})+++++++++++")
    plane = Part.Plane(plane_origin, plane_normal)
    points = bspline_obj.intersect(plane)
    actual_points = []
    #print(f"points type: {type(points)}")
    #print(f"point[0] type: {type(points[0])}")
    #print(f"points {points}")a
    # Returned, I think, a list of lists of app.vectors
    # to account for intersections that are points or lines
    # we only expect points so far
    if points:
        top_level = points[0]
        if(printouts_on):
            print("Points is True")
        if isinstance(top_level, list):
            actual_points = top_level 
            if(printouts_on): 
                print("points[0] is a List is true, actual_points = points[0]")
    else:
        if(printouts_on):
            print("Points is False")
        actual_points= points
    point_vecs =[App.Vector(p.X, p.Y, p.Z) for p in actual_points]
    if(printouts_on): 
        for v in point_vecs: 
            p_vec(v,"point_vecs")
    if(printouts_on): 
        p_vec(point_vecs[0],"point_vecs[0]") 
        p_vec(point_vecs[1],"point_vecs[1]")
    
    return point_vecs



def get_plane_equation(placement):
# Usage example:
#obj = App.ActiveDocument.ActiveObject
#if hasattr(obj, 'Placement'):
#    get_plane_equation(obj.Placement)
    # Extracts the position (Base) and rotation from the placement
    base = placement.Base
    rot = placement.Rotation
    # Example: Calculate a normal vector from the rotation
    normal = rot.multVec(App.Vector(1, 0, 0)) 
    #print(f"Position: {base}, Normal: {normal}")
    # Return equation parameters, etc.
    return base, normal




        
def main():  
    main_start=0
    print_4x4_matrix(xz_xy_place.Rotation.Matrix,"xz_xy_place")
    #print_placement(xz_xy_place.Rotation,"xz_xy_place")
    #print_placement(yz_xy_place.Rotation,"yz_xy_place")
    testxvec=App.Vector(1,0,0)
    p_vec(testxvec,"testxvec")
    testxvec=rotate_vector(testxvec,37.0)
    p_vec(testxvec,"testxvec")


if __name__ == "__main__":
    main()
    
#def build_HJh_placement():
#    #Create placement object (4x4 Transformation Matrix) 8 mm forward of Heel 
#    #having normal along A-B profile line so that it is parallel to heel section
#    uHJ_vec = (profile.profile_dwg.J - profile.profile_dwg.H).normalize() #xz_xy_place*
#    print(f"uHJ_vec ({uHJ_vec})")
#    g_uHJ_vec = xz_xy_place * uHJ_vec 
#    p_vec(g_uHJ_vec,"g_uHJ_vec") 
#    p_vec(profile.profile_dwg.H,"prfile_dwg.h")
#    g_H_vec = xz_xy_place*profile.profile_dwg.H*1.5*25.4
#    p_vec(g_H_vec,"g_H_vec")
#    p_vec(g_H_vec + 8*g_uHJ_vec,"g_H_vec + 8*g_uHJ_vec")  
#    g_nHB_vec = xz_xy_place * ( profile.profile_dwg.B - profile.profile_dwg.H).normalize()
#    p_vec(g_nHB_vec,"g_nHB_vec")
#    g_HBh_tvec = g_H_vec + g_nHB_vec*8 #8mm
#    xy_g_nHB_place = App.Placement(g_HBh_tvec,App.Rotation(nX,g_nHB_vec))
#    print_4x4_matrix(xy_g_nHB_place.Matrix,"xy_g_nHB_place.Matrix")
#    placement = xy_g_nHB_place*yz_xy_place
#    return placement
    
#def build_HJH_placement():
#    #Create placement object (4x4 Transformation Matrix) 8 mm forward of Heel 
#    #having normal along A-B profile line so that it is parallel to heel section
#    uHJ_vec = (profile.profile_dwg.J - profile.profile_dwg.H).normalize() #xz_xy_place*
#    print(f"uHJ_vec ({uHJ_vec})")
#    g_uHJ_vec = xz_xy_place * uHJ_vec 
#    p_vec(g_uHJ_vec,"g_uHJ_vec") 
#    g_H_vec = xz_xy_place*profile.profile_dwg.H
#    p_vec(g_H_vec + insole.insole_lens.AH*g_uHJ_vec,"g_H_vec + 8*g_uHJ_vec")  
#    g_nHB_vec = xz_xy_place * ( profile.profile_dwg.B - profile.profile_dwg.H).normalize()
#    p_vec(g_nHB_vec,"g_nHB_vec")
#    g_HBh_tvec = g_H_vec + g_nHB_vec*insole.insole_lens.AH
#    xy_g_nHB_place = App.Placement(g_HBh_tvec,App.Rotation(nX,g_nHB_vec))
#    print_4x4_matrix(xy_g_nHB_place.Matrix,"xy_g_nHB_place.Matrix")
#    placement = xy_g_nHB_place*yz_xy_place
#    return placement
  
   
    
      
#    print_4x4_matrix(xz_xy_place.Matrix,"xz_xy_place line 71")
#    print_4x4_matrix(yz_xy_place.Matrix,"yz_xy_place.Matrix line 73")
#    yz_xy_place_inv = yz_xy_place.inverse()
#    print_4x4_matrix(yz_xy_place_inv.Matrix,"yz_xy_place_inv.Matrix")
#    yz_xz_place = App.Placement(App.Vector(0,0,0),App.Rotation(App.Vector(0,1,0),App.Vector(-1,0,0),App.Vector(0,0,1)))
#    print_4x4_matrix(yz_xz_place.Matrix,"yz_xz_place.Matrix")
