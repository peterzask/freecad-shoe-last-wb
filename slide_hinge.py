# Macro Begin: /home/rgrabbe/00_ausr/work/freecad/macros/temp.FCMacro +++++++++++++++++++++++++++++++++++++++++++++++++
import FreeCAD as App
import Sketcher
import Part
#import SplitFeatures
#import ImportGui
import last_profile
import xs_base
import helper_funcs as hf

xb = xs_base
# Build scalable basis vector space scaffold
#Future: scale dimensions so same relative locations are hit for different last sizes and heel heights
Ob = xb.g_H
Ux = (xb.g_J - Ob).normalize()
Uy = App.Vector(0,1,0)
Uz = (xb.g_C5 - Ob).normalize()
g_H1 = last_profile.sketch_profile.Placement * last_profile.profile_dwg.H1
hf.p_vec(g_H1,"g_H1")
Scale_0 = 173.6251982742312
Scale = g_H1.Length / Scale_0
print(f"Scale = {Scale}")
hf.p_vec(Ob,"Ob")
hf.p_vec(Ux,"Ux")
hf.p_vec(Uy,"Uy")
hf.p_vec(Uz,"Uz")



V = App.Vector

SHOW_CUTTERS = False   # outer/inner stepped cutter surfaces
SHOW_BORES   = False   # jack hole + pull hole cylinders

doc = App.ActiveDocument
if doc.getObject("Shape"):
    doc.removeObject("Shape")
if doc.getObject("Shape001"):
    doc.removeObject("Shape001")
if doc.getObject("Shape002"):
    doc.removeObject("Shape002")
if doc.getObject("Shape003"):
    doc.removeObject("Shape003")
if doc.getObject("Shape004"):
    doc.removeObject("Shape004")




def make_stepped_cutter(rail_width):
    P1 = V(0, 100, 0)
    P2 = V(0, rail_width, 0)
    P3 = V(-rail_width, rail_width, 0)   
    P4 = V(-rail_width, -rail_width, 0)  
    P5 = V(0, -rail_width, 0)
    P6 = V(0, -100, 0)
    edge_list = [
        Part.makeLine(P1, P2),
        Part.makeLine(P2, P3),
        Part.makeLine(P3, P4),
        Part.makeLine(P4, P5),
        Part.makeLine(P5, P6)
    ]
    rail_edge = Part.Wire(edge_list)
    tilt = 0
    step = 40
    # Extrude and translate segments
    seg_bottom = rail_edge.extrude(V(tilt, 0, 75))
    
    seg_step = rail_edge.extrude(V(step, 0, 0))
    seg_step.translate(V(tilt, 0, 75))
    
    seg_top = rail_edge.extrude(V(tilt, 0, 75))
    seg_top.translate(V(tilt + step, 0, 75))
    
    # Combine into a single continuous thin sheet
    all_faces = seg_bottom.Faces + seg_step.Faces + seg_top.Faces
    cutting_surface = Part.makeShell(all_faces)
    
    return cutting_surface

place_cutter = App.Placement(V(25,0,20),App.Rotation(V(0,1,0),20))
outer_cutter = make_stepped_cutter(rail_width=6)
outer_cutter.Placement = place_cutter
if SHOW_CUTTERS: Part.show(outer_cutter)

inner_cutter = make_stepped_cutter(rail_width=5)
inner_cutter.Placement = place_cutter
if SHOW_CUTTERS: Part.show(inner_cutter)

jack_hole = Part.makeCylinder((3/8*25.4/2+.5), 80)
jack_hole.Placement = App.Placement( V(70, 0, 55), App.Rotation(V(0, 1, 0),5))
if SHOW_BORES: Part.show(jack_hole)

heel_pull_hole = Part.makeCylinder(2.5, 120)
heel_pull_hole.Placement = App.Placement(V(30,40,100),App.Rotation(V(1,0,0),90))
if SHOW_BORES: Part.show(heel_pull_hole)

front_pull_hole = Part.makeCylinder(2.5, 120)
front_pull_hole.Placement = App.Placement(V(110,40,100),App.Rotation(V(1,0,0),90))
if SHOW_BORES: Part.show(front_pull_hole)

# ── Cutting & Boring ─────────────────────────────────────────────────────────
import BOPTools.SplitAPI

_shoe_obj = doc.getObject("ShoeLast")
if _shoe_obj is None:
    print("ShoeLast not in document — run uv_0.py first")
else:
    shoe = _shoe_obj.Shape

    # Bore all three holes into the unified solid before splitting
    bored = shoe.cut(jack_hole).cut(heel_pull_hole).cut(front_pull_hole)

    # Split on the outer (6mm rail) stepped cutter surface
    sliced = BOPTools.SplitAPI.slice(bored, [outer_cutter], 'Split', tolerance=0.05)
    pieces = sorted(sliced.Solids, key=lambda s: s.BoundBox.Center.x)

    if len(pieces) == 2:
        Part.show(pieces[0], "HeelSection")
        Part.show(pieces[1], "FrontSection")
        print(f"Split OK — heel xmax={pieces[0].BoundBox.XMax:.1f}  "
              f"front xmin={pieces[1].BoundBox.XMin:.1f}")
    else:
        print(f"Split gave {len(pieces)} pieces (expected 2)")
        for i, p in enumerate(pieces):
            Part.show(p, f"Piece_{i}")

    doc.recompute()




































#dead code
"""
P1=  hf.xz_xy_place *  App.Vector(97.050346,131.802841,0)
P2 = hf.xz_xy_place *  App.Vector(73.879822,69.509766,0)
P3=  hf.xz_xy_place *  App.Vector(51.276585,76.371468,0)
P4 = hf.xz_xy_place *  App.Vector(26.655190,4.525461,0)
cutter_edge_list=[]
cutter_edge_list.append(Part.makeLine(P1,P2))
cutter_edge_list.append(Part.makeLine(P2,P3))
cutter_edge_list.append(Part.makeLine(P3,P4))
cutter_wire = Part.Wire(cutter_edge_list)
cutter = cutter_wire.extrude(App.Vector(0,200,0))
cutter.Placement = App.Placement(App.Vector(0,-100,0),App.Rotation())

#Part.show(cutter)

RAIL = 6.0  # mm square
"""
"""
def _vertical_rail_box(p_lo, p_hi):
    #Vertical (Z) rail slot: 6mm wide in X, 6mm deep straddling cut plane in Y,
    #spanning the full Z height of the riser.  Both halves get a 3mm-deep groove.
    mid_x = (p_lo.x + p_hi.x) / 2
    z_min = min(p_lo.z, p_hi.z)
    z_max = max(p_lo.z, p_hi.z)
    return Part.makeBox(
        RAIL, RAIL, z_max - z_min,
        App.Vector(mid_x - RAIL/2, -RAIL/2, z_min))

hf.p_vec(P1,"P1")
hf.p_vec(P2,"P2")
hf.p_vec(P3,"P3")
hf.p_vec(P4,"P4")
hf.p_vec(xb.g_H,"xb.g_H")

"""
"""
# Gui.runCommand('Std_DlgMacroRecord',0)
# Gui.runCommand('Sketcher_CreatePolyline',0)
App.getDocument('Unnamed').getObject('Sketch').addGeometry(Part.LineSegment(App.Vector(97.050346,131.802841,0),App.Vector(73.879822,69.509766,0)),False)
App.getDocument('Unnamed').getObject('Sketch').addGeometry(Part.LineSegment(App.Vector(73.879822,69.509766,0),App.Vector(51.276585,76.371468,0)),False)
App.getDocument('Unnamed').getObject('Sketch').addConstraint(Sketcher.Constraint('Coincident',0,2,1,1)) 
App.getDocument('Unnamed').getObject('Sketch').addGeometry(Part.LineSegment(App.Vector(51.276585,76.371468,0),App.Vector(26.655190,4.525461,0)),False)
App.getDocument('Unnamed').getObject('Sketch').addConstraint(Sketcher.Constraint('Coincident',1,2,2,1)) 
# Gui.Selection.addSelection('Unnamed','Sketch','Edge1',94.3975,-0.00801486,124.671,False)
# Gui.Selection.addSelection('Unnamed','Sketch','Edge2',55.0586,-0.00800897,75.2234,False)
# Gui.Selection.addSelection('Unnamed','Sketch','Edge3',33.8921,-0.00800306,25.6429,False)
# Gui.Selection.setPreselection(App.getDocument('Unnamed').getObject('Sketch'),'Edge1',tp=2)
# Gui.getDocument('Unnamed').resetEdit()
App.ActiveDocument.recompute()
# ActiveSketch = App.getDocument('Unnamed').getObject('Sketch')
# tv = ActiveSketch.ViewObject.TempoVis
# if tv:
#   tv.restore()
# ActiveSketch.ViewObject.TempoVis = None
# del(tv)
# del(ActiveSketch)
# 
# Gui.Selection.addSelection('Unnamed','Sketch')
App.getDocument('Unnamed').recompute()
# Gui.Selection.clearSelection()
# Gui.Selection.addSelection('Unnamed','Sketch','Edge1',94.0115,-1.47382e-05,123.633)
# Gui.Selection.addSelection('Unnamed','PegHole','Face1',58.4966,-26.5597,75.6)
# Gui.Selection.addSelection('Unnamed','Sketch','Edge3',28.4844,-1.17578e-06,9.86317)
# Gui.Selection.clearSelection()
# Gui.Selection.addSelection('Unnamed','PegHole','Face1')
# Gui.runCommand('Std_ToggleVisibility',0)
# Gui.Selection.clearSelection()
# Gui.Selection.addSelection('Unnamed','Sketch','Edge1',84.3495,-1.16416e-05,97.6571)
# Gui.Selection.addSelection('Unnamed','Sketch','Edge2',54.794,-8.9769e-06,75.3037)
# Gui.Selection.addSelection('Unnamed','Sketch','Edge3',38.9343,-4.81085e-06,40.3564)
# Gui.Selection.setPreselection(App.getDocument('Unnamed').getObject('Sketch'),'Edge3',tp=2)
# Gui.Selection.setPreselection(App.getDocument('Unnamed').getObject('Sketch'),'Edge2',tp=2)
# Gui.Selection.setPreselection(App.getDocument('Unnamed').getObject('Sketch'),'Edge1',tp=2)
# Gui.runCommand('Part_Extrude',0)
# Gui.Selection.setPreselection(App.getDocument('Unnamed').getObject('Sketch'),'Edge1',tp=2)
# Gui.Selection.setPreselection(App.getDocument('Unnamed').getObject('Sketch'),'Edge3',tp=2)
App.getDocument('Unnamed').addObject('Part::Extrusion','Extrude')
f = App.getDocument('Unnamed').getObject('Extrude')
f.Base = App.getDocument('Unnamed').getObject('Sketch')
f.DirMode = "Normal"
f.DirLink = None
f.LengthFwd = 200.000000000000000
f.LengthRev = 0.000000000000000
f.Solid = False
f.Reversed = False
f.Symmetric = True
f.TaperAngle = 0.000000000000000
f.TaperAngleRev = 0.000000000000000
App.getDocument('Unnamed').getObject('Sketch').Visibility = False
App.ActiveDocument.recompute()
# Gui.Selection.clearSelection()
# Gui.Selection.addSelection('Unnamed','Extrude')
# Gui.Selection.clearSelection()
# Gui.Selection.addSelection('Unnamed','PegHole')
# Gui.runCommand('Std_ToggleVisibility',0)
# Gui.Selection.addSelection('Unnamed','Extrude','Face1',88.7846,-58.3085,109.581)
# Gui.Selection.addSelection('Unnamed','Extrude','Face2',61.4884,-70.0146,73.2714)
# Gui.Selection.addSelection('Unnamed','Extrude','Face3',42.3836,-73.4528,50.4214)
### Begin command Part_CompSplitFeatures
f = BOPTools.SplitFeatures.makeSlice(name='Slice')
f.Base = [App.ActiveDocument.PegHole, App.ActiveDocument.Extrude][0]
f.Tools = [App.ActiveDocument.PegHole, App.ActiveDocument.Extrude][1:]
f.Mode = 'Split'
f.Proxy.execute(f)
f.purgeTouched()
for obj in f.ViewObject.Proxy.claimChildren():
    obj.ViewObject.hide()
CompoundTools.Explode.explodeCompound(f)
f.ViewObject.hide()
App.ActiveDocument.recompute()
### End command Part_CompSplitFeatures
# Gui.Selection.clearSelection()
# Gui.Selection.addSelection('Unnamed','Slice_child0')
# Gui.Selection.clearSelection()
# Gui.Selection.addSelection('Unnamed','Slice_child1')
# Gui.Selection.clearSelection()
# Gui.Selection.addSelection('Unnamed','Slice_child0')
# Gui.Selection.setPreselection(App.getDocument('Unnamed').getObject('Slice_child0 (Slice'),'0)',tp=2)
### Begin command Std_Export
__objs__ = []
__objs__.append(FreeCAD.getDocument("Unnamed").getObject("Slice_child0"))
if hasattr(ImportGui, "exportOptions"):
    options = ImportGui.exportOptions(u"/home/rgrabbe/00_ausr/work/freecad/3d_prints/Unnamed-Slice.0.3mf")
    ImportGui.export(__objs__, u"/home/rgrabbe/00_ausr/work/freecad/3d_prints/Unnamed-Slice.0.3mf", options)
else:
    ImportGui.export(__objs__, u"/home/rgrabbe/00_ausr/work/freecad/3d_prints/Unnamed-Slice.0.3mf")

del __objs__
### End command Std_Export
# Gui.Selection.clearSelection()
# Gui.Selection.addSelection('Unnamed','Slice_child1')
# Gui.Selection.setPreselection(App.getDocument('Unnamed').getObject('Slice_child1 (Slice'),'1)',tp=2)
### Begin command Std_Export
__objs__ = []
__objs__.append(FreeCAD.getDocument("Unnamed").getObject("Slice_child1"))
if hasattr(ImportGui, "exportOptions"):
    options = ImportGui.exportOptions(u"/home/rgrabbe/00_ausr/work/freecad/3d_prints/Unnamed-Slice.1.3mf.step")
    ImportGui.export(__objs__, u"/home/rgrabbe/00_ausr/work/freecad/3d_prints/Unnamed-Slice.1.3mf.step", options)
else:
    ImportGui.export(__objs__, u"/home/rgrabbe/00_ausr/work/freecad/3d_prints/Unnamed-Slice.1.3mf.step")

del __objs__
### End command Std_Export
# Gui.Selection.clearSelection()
# Gui.Selection.addSelection('Unnamed','Slice_child0','Face1',55.1707,-10.3496,111.133)
# Gui.Selection.setPreselection(App.getDocument('Unnamed').getObject('Slice_child0'),'Face1',tp=2)
### Begin command Std_Export
__objs__ = []
__objs__.append(FreeCAD.getDocument("Unnamed").getObject("Slice_child0"))
if hasattr(ImportGui, "exportOptions"):
    options = ImportGui.exportOptions(u"/home/rgrabbe/00_ausr/work/freecad/3d_prints/Unnamed-Slice.0.step")
    ImportGui.export(__objs__, u"/home/rgrabbe/00_ausr/work/freecad/3d_prints/Unnamed-Slice.0.step", options)
else:
    ImportGui.export(__objs__, u"/home/rgrabbe/00_ausr/work/freecad/3d_prints/Unnamed-Slice.0.step")

del __objs__
### End command Std_Export
# Gui.Selection.setPreselection(App.getDocument('Unnamed').getObject('Slice_child0'),'Face1',tp=2)
### Begin command Std_Export
__objs__ = []
__objs__.append(FreeCAD.getDocument("Unnamed").getObject("Slice_child0"))
if hasattr(ImportGui, "exportOptions"):
    options = ImportGui.exportOptions(u"/home/rgrabbe/00_ausr/work/freecad/3d_prints/Unnamed-Slice.0.step")
    ImportGui.export(__objs__, u"/home/rgrabbe/00_ausr/work/freecad/3d_prints/Unnamed-Slice.0.step", options)
else:
    ImportGui.export(__objs__, u"/home/rgrabbe/00_ausr/work/freecad/3d_prints/Unnamed-Slice.0.step")

del __objs__
### End command Std_Export
# Gui.Selection.clearSelection()
# Gui.Selection.addSelection('Unnamed','Slice_child1')
# Gui.Selection.setPreselection(App.getDocument('Unnamed').getObject('Slice_child1 (Slice'),'1)',tp=2)
### Begin command Std_Export
__objs__ = []
__objs__.append(FreeCAD.getDocument("Unnamed").getObject("Slice_child1"))
if hasattr(ImportGui, "exportOptions"):
    options = ImportGui.exportOptions(u"/home/rgrabbe/00_ausr/work/freecad/3d_prints/Unnamed-Slice.1.step")
    ImportGui.export(__objs__, u"/home/rgrabbe/00_ausr/work/freecad/3d_prints/Unnamed-Slice.1.step", options)
else:
    ImportGui.export(__objs__, u"/home/rgrabbe/00_ausr/work/freecad/3d_prints/Unnamed-Slice.1.step")

del __objs__
### End command Std_Export
# Macro End: /home/rgrabbe/00_ausr/work/freecad/macros/temp.FCMacro +++++++++++++++++++++++++++++++++++++++++++++++++
"""
