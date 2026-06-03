import FreeCAD as App
import Part

def add_bsplines_to_named_shape(obj_name="MySplineContainer", poles_lists=None):
    """
    Creates multiple BSpline curves, encapsulates them into an OCCT Compound,
    and displays them under a named Part Feature, auto-refreshing previous instances.
    
    :param obj_name: The internal string name of the FreeCAD document object.
    :param poles_lists: A list of lists containing App.Vector elements for the BSpline poles.
    """
    doc = App.activeDocument()
    if not doc:
        doc = App.newDocument("Unsaved_Geometry_Doc")
    
    # 1. Fallback dummy data if no coordinates are supplied
    if poles_lists is None:
        poles_lists = [
            [App.Vector(0, 0, 0), App.Vector(10, 20, 0), App.Vector(20, 0, 10), App.Vector(30, 10, 0)],
            [App.Vector(0, 10, 0), App.Vector(10, -10, 5), App.Vector(20, 30, -5), App.Vector(30, 0, 0)]
        ]
        
    edges = []
    
    # 2. Generate individual BSpline curves and turn them into TopoDS shapes (Edges)
    for poles in poles_lists:
        bspline = Part.BSplineCurve()
        # Interpolate provides a quick way to construct a smooth curve passing through points
        bspline.interpolate(poles) 
        edges.append(bspline.toShape())
        
    # 3. Pack all geometry elements into a single OCCT Shape container
    compound_container = Part.Compound(edges)
    
    # 4. Find the existing document object or create a new one to prevent duplication
    obj = doc.getObject(obj_name)
    
    if obj is None:
        # Create a clean feature if it doesn't exist yet
        obj = doc.addObject("Part::Feature", obj_name)
        obj.Label = obj_name  # Label displayed in the Tree View
        
    # 5. Overwrite the old container shape with the newly generated compound
    obj.Shape = compound_container
    
    # 6. Flush modifications, recalculate the dependency graph, and refresh the UI viewport
    doc.recompute()
    
    # Force visibility in the 3D window if it was hidden
    if App.GuiUp:
        import FreeCADGui as Gui
        gui_obj = Gui.ActiveDocument.getObject(obj_name)
        if gui_obj:
            gui_obj.show()
            
    print(f"Successfully updated OCCT container shape: '{obj_name}'")

# --- Execution ---
# Copy and paste this whole block into the FreeCAD Python Console to execute it.
add_bsplines_to_named_shape("Named_Spline_Container")
