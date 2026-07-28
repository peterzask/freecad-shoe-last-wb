import FreeCAD as App 
import Part
import Draft
import helper_funcs as hf
import last_insole
import last_profile
import gc
import importlib
importlib.reload(hf) #helper_funcs)

# Add point-name text overlays to the 3d insole and profile drawings.
# To hide, select TextGroups in tree and hit spacebar.
# Only run if user executes this.

def control_curve_text(poles:list[App.Vector], normal:App.Vector, height:float, sketch):
    if not sketch:
        print(f"text_overlay error: Sketch not open")
        return
    doc = sketch.Document
    cct_name = "control_curve_text"
    existing = doc.getObject(cct_name)
    if existing:
        # removeObject() only deletes the group container, not its
        # ShapeString children — remove those first or they orphan and
        # pile up on every re-run.
        for child in existing.Group:
            doc.removeObject(child.Name)
        doc.removeObject(cct_name)
    group_shapestring_container = doc.addObject("App::DocumentObjectGroup", cct_name)

    import os as _os
    font_path = _os.path.expanduser("~/.local/share/fonts/FreeSansBold.ttf")
    if not _os.path.exists(font_path):
        font_path = "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf"

    # build text
    for j, p in enumerate(poles):
        if normal.z == 1.0:
            label_pt = p + App.Vector(1,1,0)
        else:
            label_pt = p + App.Vector(1,0,1)
        ss_obj = Draft.make_shapestring(
                String = f"{j}",
                FontFile = font_path,
                Size = height,
                Tracking = 0.0)
        ss_obj.Placement = App.Placement(
            sketch.Placement.multVec(label_pt), sketch.Placement.Rotation)
        group_shapestring_container.addObject(ss_obj)













def main():
    doc = App.ActiveDocument
    if doc is None:
        print("text_overlay: no active document.")
        return

    existing_groups = [o.Label for o in doc.findObjects("App::DocumentObjectGroup")]
    if "InsoleTextGroup" in existing_groups and "ProfileTextGroup" in existing_groups:
        print("text_overlay: groups exist — delete InsoleTextGroup and ProfileTextGroup to regenerate.")
        return

    #sketch_name = "sketch_insole_text"
    #doc, sketch_insole_text = hf.Doc_Sketch(None, sketch_name)

    #Assemble profile drawing point names and positions.
    p_cp_text_names = ["H","K1","K","Kb","J","B","B1","B2","J1","H1","E","C5E_intercept","C5","H2"]            
    p_cp_show_switch= [  1,   1,  1,   1,  1,   1,  1,   1,   1,   1,  1,              1,   1,   1]
    p_cp_positions =[ App.Vector(last_profile.profile_dwg.H),             
        App.Vector(last_profile.profile_dwg.K1),            
        App.Vector(last_profile.profile_dwg.K),             
        App.Vector(last_profile.profile_dwg.Kb),            
        App.Vector(last_profile.profile_dwg.J),             
        App.Vector(last_profile.profile_dwg.B),             
        App.Vector(last_profile.profile_dwg.B1),            
        App.Vector(last_profile.profile_dwg.B2),            
        App.Vector(last_profile.profile_dwg.J1),            
        App.Vector(last_profile.profile_dwg.H1),            
        App.Vector(last_profile.profile_dwg.E),             
        App.Vector(last_profile.profile_dwg.C5E_intercept), 
        App.Vector(last_profile.profile_dwg.C5),            
        App.Vector(last_profile.profile_dwg.H2)]            
    
    
    # vo is used to match Joint positions, pt J on insole to profile's point J (Joint). 
    vo = App.Vector(last_insole.insole_lens.CJ+2,0,0)
    # Text offset move text a little to upper right of point
    text_offset=App.Vector(2,2,0)
    import os as _os
    font_path = _os.path.expanduser("~/.local/share/fonts/FreeSansBold.ttf")
    if not _os.path.exists(font_path):
        font_path = "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf"


    def build_profile_text():
        #Rotate local xy translation vectors to xz
        for j in range(len(p_cp_positions)):
            p_cp_positions[j] = hf.xz_xy_place.multVec(p_cp_positions[j]+vo+text_offset)
            #hf.p_vec(p_cp_positions[j],p_cp_text_names[j])
        

        p_shapestring_objects = []
        for j, t in enumerate(p_cp_text_names):
            if p_cp_show_switch[j] == 1:
                ss_obj = Draft.make_shapestring(
                        String= t,
                        FontFile = font_path,
                        Size = 10.0,
                        Tracking = 0.0)
                ss_obj.Placement = App.Placement(p_cp_positions[j],hf.xz_xy_place.Rotation)
                p_shapestring_objects.append(ss_obj)
            
        p_group_shapestring_container = doc.addObject("App::DocumentObjectGroup", "ProfileTextGroup")
        for obj in p_shapestring_objects:
            p_group_shapestring_container.addObject(obj)

    #Assemble insole drawing point names and positions.
    i_cp_text_names = ["A", "B", "B1", "B2", "C", "D", "J", "J1", "J2", "H", "H1", "H2", "H3", "H4", "O"]
    i_cp_show_switch =[ 1 ,  1 ,   1 ,   1 ,  1 ,  1 ,  1 ,   1 ,   1 ,  1 ,   1 ,   1 ,   1 ,   1 ,  1 ]
    i_cp_positions = [App.Vector(last_insole.insole_dwg.A), 
                    App.Vector(last_insole.insole_dwg.B), 
                    App.Vector(last_insole.insole_dwg.B1), 
                    App.Vector(last_insole.insole_dwg.B2), 
                    App.Vector(last_insole.insole_dwg.C), 
                    App.Vector(last_insole.insole_dwg.D), 
                    App.Vector(last_insole.insole_dwg.J), 
                    App.Vector(last_insole.insole_dwg.J1), 
                    App.Vector(last_insole.insole_dwg.J2), 
                    App.Vector(last_insole.insole_dwg.H), 
                    App.Vector(last_insole.insole_dwg.H1), 
                    App.Vector(last_insole.insole_dwg.H2), 
                    App.Vector(last_insole.insole_dwg.H3), 
                    App.Vector(last_insole.insole_dwg.H4),
                    App.Vector(last_insole.insole_dwg.O)] 

    def build_insole_text():
        # xy translation vectors
        for j in range(len(i_cp_positions)):
            i_cp_positions[j] = i_cp_positions[j]+text_offset
            #hf.p_vec(i_cp_positions[j],i_cp_text_names[j])


        i_shapestring_objects = []
        for j, t in enumerate(i_cp_text_names):
            if i_cp_show_switch[j] == 1: 
                ss_obj_2 = Draft.make_shapestring(
                        String= t,
                        FontFile = font_path,
                        Size = 10.0,
                        Tracking = 0.0)
                ss_obj_2.Placement = App.Placement(i_cp_positions[j],App.Rotation(0,0,0))
                i_shapestring_objects.append(ss_obj_2)

        i_group_shapestring_container = doc.addObject("App::DocumentObjectGroup", "InsoleTextGroup")
        for obj in i_shapestring_objects:
            i_group_shapestring_container.addObject(obj)

    build_insole_text()
    build_profile_text()

    doc.recompute()
if __name__ == "__main__":
    main()

    """
#doc.removeObject(obj_name) 
# gc.collect() 
.A, 
.B, 
.B1,
.B2,
.C, 
.D, 
.J, 
.J1,
.J2,
.H, 
.H1,
.H2,
.H3,
.H4,
.O, 
    """
