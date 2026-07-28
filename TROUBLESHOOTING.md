/ 1 /
/******** Attribute deleted ************/
Restart Freecad if you see an "Attribute Deleted Error Like below ".
Example:

  File "/home/rgrabbe/00_ausr/work/freecad/macros/control_curves.py", line 224, in build
    pd      = last_profile.profile_dwg
               ^^^^^^^^^^^^^^^^^^^
  File "/home/rgrabbe/00_ausr/work/freecad/macros/control_curves.py", line 172, in _section_geometry
    skp = last_profile.sketch_profile
           ^^^^^^^^^^^^^

Cannot access attribute 'Placement' of deleted object


Reason:
Cannot access attribute 'Placement' of deleted object means last_profile.sketch_profile is
  a Python wrapper pointing to a FreeCAD Sketch object that was deleted from the document during your exploration session. The Python
  reference is still alive, the FreeCAD C++ object underneath it is gone.

