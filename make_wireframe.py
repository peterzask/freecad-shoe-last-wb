import inspect
import importlib
import FreeCAD as App
import FreeCADGui
import Part
import helper_funcs as hf
import last_insole
import last_profile
import xs_base
import xs_0, xs_1, xs_2, xs_3, xs_4, xs_5, xs_6, xs_7, xs_8

#For now, user must know everthing must be up to date before running.
#importlib.reload(hf)
#importlib.reload(last_insole)
#importlib.reload(last_profile)
#importlib.reload(xs_base)
#for _m in [xs_0, xs_1, xs_2, xs_3, xs_4, xs_5, xs_6, xs_7, xs_8]:
#    importlib.reload(_m)

print(f"+++++++++++++++Line({inspect.currentframe().f_lineno}) File:({__file__})+++++++++++++++++++")

# Build rows the same way uv_0 does — no NURBS, no solid, no export
xs_list = [
    (xs_0.xs_0, xs_base.xs_0_placement),
    (xs_1.xs_1, xs_base.xs_1_placement),
    (xs_2.xs_2, xs_base.xs_2_placement),
    (xs_3.xs_3, xs_base.xs_3_placement),
    (xs_4.xs_4, xs_base.xs_4_placement),
    (xs_5.xs_5, xs_base.xs_5_placement),
    (xs_6.xs_6, xs_base.xs_6_placement),
    (xs_7.xs_7, xs_base.xs_7_placement),
    (xs_8.xs_8, xs_base.xs_8_placement),
]
crisp_sole = False
#rows = [list(xs_base.get_heel_end_row(crisp_sole=xs_base.CRISP_SOLE))]  # heel end cap (global 3D)
rows = [list(xs_base.get_heel_end_row(crisp_sole))]  # heel end cap (global 3D)
for xs, placement in xs_list:
    pl = placement * hf.yz_xy_place
    #rows.append([pl.multVec(pv) for pv in xs.ctrl.control_points(crisp_sole=xs_base.CRISP_SOLE)])
    rows.append([pl.multVec(pv) for pv in xs.ctrl.control_points(crisp_sole)])


u_count = len(rows)
v_count = len(rows[0])
print(f"wireframe: u_count={u_count}, v_count={v_count}")


def make_wireframe(rows):
    u_count = len(rows)
    v_count = len(rows[0])
    all_wires = []
    for u in range(u_count):
        row_edges = []
        for v in range(v_count - 1):
            row_edges.append(Part.LineSegment(rows[u][v], rows[u][v+1]).toShape())
        if row_edges:
            all_wires.append(Part.Wire(row_edges))
    for v in range(v_count):
        col_edges = []
        for u in range(u_count - 1):
            col_edges.append(Part.LineSegment(rows[u][v], rows[u+1][v]).toShape())
        if col_edges:
            all_wires.append(Part.Wire(col_edges))
    try:
        wireframe_shape = Part.makeCompound(all_wires)
        Part.show(wireframe_shape, "UV_Wireframe_Grid")
        App.ActiveDocument.recompute()
        print("Wireframe created.")
    except Exception as e:
        print(f"Failed to create wireframe: {e}")


def make_faces(wireframe_data):
    u_len = len(wireframe_data)
    v_len = len(wireframe_data[0])
    doc   = App.activeDocument() or App.newDocument("WireframeSurfaces")
    faces = []
    for u in range(0, u_len - 1):
        for v in range(0, v_len - 1):
            edges = []
            a=u  ; b=v  ; c=u+1; d=v  ; edges.append(Part.makeLine(wireframe_data[a][b], wireframe_data[c][d]))
            a=u+1; b=v  ; c=u+1; d=v+1; edges.append(Part.makeLine(wireframe_data[a][b], wireframe_data[c][d]))
            a=u+1; b=v+1; c=u  ; d=v+1; edges.append(Part.makeLine(wireframe_data[a][b], wireframe_data[c][d]))
            a=u  ; b=v+1; c=u  ; d=v  ; edges.append(Part.makeLine(wireframe_data[a][b], wireframe_data[c][d]))
            wire = Part.Wire(edges)
            if wire.isClosed():
                face = Part.makeFilledFace(wire.Edges)
                faces.append(face)
            else:
                App.Console.PrintWarning(f"[{u},{v}] did not form a closed loop.\n")
    surface_compound = Part.makeCompound(faces)
    obj_name = "WireframeSurfaces"
    if doc.getObject(obj_name):
        doc.removeObject(obj_name)
    part_obj = doc.addObject("Part::Feature", obj_name)
    part_obj.Shape = surface_compound
    doc.recompute()
    print(f"Wireframe faces: {len(faces)} quads")


make_faces(rows)

print("\nThe end\n")
