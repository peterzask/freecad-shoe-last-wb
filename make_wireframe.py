import inspect
import importlib
import FreeCAD as App
import FreeCADGui
import Part
import helper_funcs as hf
import last_insole
import last_profile
import xs_base
import xs_heel_near
import xs_0, xs_1, xs_2, xs_3, xs_4, xs_5, xs_6, xs_7, xs_8, xs_9
import uv_0

importlib.reload(xs_base)
importlib.reload(xs_heel_near)
for _m in [xs_0, xs_1, xs_2, xs_3, xs_4, xs_5, xs_6, xs_7, xs_8, xs_9]:
    importlib.reload(_m)

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
    (xs_9.xs_9, xs_base.xs_9_placement),
]
crisp_sole = False #xs_base.CRISP_SOLE #  should always be False, 0 width wireframes crash
#rows = [list(xs_base.get_heel_end_row(crisp_sole=xs_base.CRISP_SOLE))]  # heel end cap (global 3D)
rows = [list(xs_base.get_heel_end_row(crisp_sole))]       # heel end cap
pl_hn = xs_base.xs_heel_near_placement * hf.yz_xy_place
rows.append(xs_heel_near.xs_heel_near.row_world(pl_hn, crisp_sole))
for xs, placement in xs_list:
    pl = placement * hf.yz_xy_place
    #rows.append([pl.multVec(pv) for pv in xs.ctrl.control_points(crisp_sole=xs_base.CRISP_SOLE)])
    rows.append([pl.multVec(pv) for pv in xs.ctrl.control_points(crisp_sole)])
rows.append(list(xs_base.xs_toe_end_row_plain))

u_count = len(rows)
v_count = len(rows[0])
print(f"wireframe: u_count={u_count}, v_count={v_count}")

if False:
    def qmake_wireframe(rows):
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
    print(f"u_len({u_len}) v_len({v_len})")
    for u in range(0, u_len - 1):
        for v in range(0, v_len - 1):
            print(f"u({u}) v({v})")
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




def wire_frame_from_bsplinesurface():
    rows = _dedupe_v_columns(uv_0.rows, 5)
    u_count = uv_0.nurb.NbUPoles
    v_count = len(rows[0])
    print(f"ucount {u_count} vcount {v_count}")
    # Chord-length parameterization in u along the C-point spine (C is at v_count//2 + 1)
    degree = 1
    C_idx = v_count // 2 + 1
    uks_raw = [0.0]
    for u in range(1, u_count):
        uks_raw.append(uks_raw[-1] + (rows[u][C_idx] - rows[u-1][C_idx]).Length)
    # plain for-loop, not a comprehension — a comprehension's expression body
    # runs in its own scope that skips right past the class body, so
    # `uks_raw` (a class-body name) isn't visible to it and raises NameError.
    _u_total = uks_raw[-1]
    for i in range(len(uks_raw)):
        uks_raw[i] = uks_raw[i] / _u_total
    uks, u_mults = _hartley_judd_knots(uks_raw, degree)

    # Chord-length parameterization in v around the xs_3 cross-section (index 5: heel_end + xs_heel_near + xs_0..xs_2)
    vks_raw = [0.0]
    for v in range(1, v_count):
        vks_raw.append(vks_raw[-1] + (rows[5][v] - rows[5][v-1]).Length)
    _v_total = vks_raw[-1]
    for i in range(len(vks_raw)):
        vks_raw[i] = vks_raw[i] / _v_total
    vks, v_mults = _hartley_judd_knots(vks_raw, degree)
    wire_frame = Part.BSplineSurface()
    wire_frame.buildFromPolesMultsKnots(
            rows,u_mults,v_mults,uks, vks,
            uperiodic=False, vperiodic=False,
            udegree=degree, vdegree=degree)
    wire_frame_shape = wire_frame.toShape()
    Part.show(wire_frame_shape)
    doc.recompute()




