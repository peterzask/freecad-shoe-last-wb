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
for _n in ["Shape", "Shape001", "Shape002", "Shape003", "Shape004",
           "HeelSection", "HeelSection001", "FrontSection", "FrontSection001"]:
    if doc.getObject(_n):
        doc.removeObject(_n)




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

# outer_cutter (6mm): open shell surface that slices the last — leaves a 6mm channel in HeelSection.
place_cutter = App.Placement(V(25,0,20),App.Rotation(V(0,1,0),20))
outer_cutter = make_stepped_cutter(rail_width=6)
outer_cutter.Placement = place_cutter
if SHOW_CUTTERS: Part.show(outer_cutter)

# strip_solid: 1mm ring face extruded along the stepped path — subtracted from FrontSection rail
# to trim it from 6mm to 5mm width, giving ~0.5mm sliding clearance per side.
# Built as a solid so .cut() works; BOPTools shell-on-shell slice fails for nested surfaces.
_tilt = 0; _step = 40
_sw = Part.Wire([
    Part.makeLine(V(0,6,0),   V(-6,6,0)),
    Part.makeLine(V(-6,6,0),  V(-6,-6,0)),
    Part.makeLine(V(-6,-6,0), V(0,-6,0)),
    Part.makeLine(V(0,-6,0),  V(0,-5,0)),
    Part.makeLine(V(0,-5,0),  V(-5,-5,0)),
    Part.makeLine(V(-5,-5,0), V(-5,5,0)),
    Part.makeLine(V(-5,5,0),  V(0,5,0)),
    Part.makeLine(V(0,5,0),   V(0,6,0)),
])
_sf = Part.Face(_sw)
_s_bot = _sf.extrude(V(_tilt, 0, 75))
_sf2 = _sf.copy(); _sf2.translate(V(_tilt + _step, 0, 75))
_s_top = _sf2.extrude(V(0, 0, 75))
_s_step = (Part.makeBox(_step + 2, 1, 2, V(-1, 5, 74))
           .fuse(Part.makeBox(_step + 2, 1, 2, V(-1, -6, 74))))
strip_solid = _s_bot.fuse(_s_top).fuse(_s_step)
strip_solid.Placement = place_cutter

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

    # Split with outer_cutter (6mm) only — confirmed working
    sliced = BOPTools.SplitAPI.slice(bored, [outer_cutter], 'Split', tolerance=0.05)
    pieces = sorted(sliced.Solids, key=lambda s: s.BoundBox.Center.x)

    if len(pieces) == 2:
        Part.show(pieces[0], "HeelSection")
        front_trimmed = pieces[1].cut(strip_solid)  # trim rail 6mm→5mm for sliding clearance
        Part.show(front_trimmed, "FrontSection")
        print(f"Split OK — heel xmax={pieces[0].BoundBox.XMax:.1f}  "
              f"front xmin={pieces[1].BoundBox.XMin:.1f}")
    else:
        print(f"Split gave {len(pieces)} pieces (expected 2)")
        for i, p in enumerate(pieces):
            Part.show(p, f"Piece_{i}")

    doc.recompute()





