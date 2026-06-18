readme.txt: 
Purpose:
This project's goal is to produce an opensource, shoelast-making-workbench or set of macros for FreeCAD 
suitable for 3d printing and last lathe making of shoelast.
Robert Grabbe, April 2026.

This project uses FreeCAD, python, and Opencascade Technologies software amoung the many libraries used by FreeCAD,
to implement the geometrical shoelast models presented in George Koleff's book "Last Designing and Making Manual,
based on the geometric method", 1997. The 'geometric methods' originate in the 1850's era when Robert Knoefel 
presented a geometric method for shoe pattern making.[1] The geometrical ratios used in these designs were likely deduced 
empirically and only presented as final designs without reference to methods or models.
Modern shoelast manufacturing companies have proprietary technology tools which are not available to the general public.
This project's success will be measured by how many gain access to this technology.
There are currently some other subscription tools available for last designing, too.

King Edward II of England proclaimed the barleycorn as the official shoe size increment in 1284 to 1327. This standardization
helped to create a more consistent measurement system for shoe sizes. But it's more than just the barleycorn. In the
following, and it allowed the making of standardized shoelast sets.

Last tables show ball, waist, and instep meausrement grths by width in letters A,B,C,D... and length  in sizes 9,9 1/2, 10,...
The ball, waist, and instep girths increase 1/4" per width, and 1/4" per full length. 

Robert Knoefel concept generated empirical, ratiometric-geometric models for shoe patterns. A geometric paper design can
be made for off the shelf shoe sizes that proportion insole shapes and last profiles.


Aesthetic and anatomical insights

The shape of shoelast toes are ubiquitously pointed. F.D. Golding (2) notes, "It also gives a reason why shoes that are designed with the
inside of the fore part tapering slightly away from the line ab, Fig. 62, are comfortable, and do not cause the foot to be misalligned."
Golding finds that for every 1/2" the heel is raised, the inner tapper increases by 1/9". His disccussion is about an angle, yet he presents
a linear distance and no radius for an arc. Since last grading was well understood in this era, 1902 edition, a size 8 last was
a typical reference size. I construe that a size 8 men's last from ball to big toe joint would be the radius for the arc length of 1/9" 
per 1/2" of heel height. Heel height and toe spring cause the same angulation at the joint. A 1/2" toe spring height would be 3/2*1/2 or
3/4" heel equivalent their ratios of last length being 1/3 on toe side to 2/3 from joint to heel.
Also, heel height, following Golding, moves the insole's ball line forward by 1/18" per 1/2" of heel height. My examinaton of an
accurate skeletal foot's firt metarsal head shows the joint surface angulatin toward te center line of the foot. Golding does advocate for
the observance and measurement of a toe moving along a line toward foot's length center line, too.


The "good" fit of a last about a foot's measurements is nicely shown in pictures of a "fitting last" that Lee Miller took which prescribe,
in notes written on the last, that the heel, instep and waist of a last be "two-widths" narrower 
while the joint is full measure and the small-toes region of the foot outline extend forward by the length 
of the big toe's first joint's length on the last, leaving room for them as the foot slides forward during a stride. It
also prescribes an insole width on the 5th metatarsal as exteneding back toware the heel to adequately support that joint to
avoid a "tailor's bunion". (Pictures seen on Lee Miller's Texas Traditions instagram page).

Two widths smaller, a width of circumference in the instep is 1/4"[3], making a 1/2" smaller circumference. A very snug fit in the
heel and instep. But, note that the underside of a shoe last crowns upward holding the bottom of the foot firmly there, recall how high of a 
instep crown some last have above the instep, giving relief so they don't digin to the top of the foot. Footwear that holds the
foot are extraordinary when they leave room for toes and pinkeys.

Conclusion: Hold the foot, point the medial toe line abit and leave space for the pinkeys. I descern from old paintings and
murals what the shoemaking masters of those eras could build and make the wealthy comfortable in or least vainly comfortable in. 
Some of the turn shoes of those eras looked very comfortable and agile.






Project Workflow:

foot_measurements

-> insole (xy plane orthographic view with length along x-axis, width aligned heel-2nd metatarsal along y-axis)
-> profile (xz plane orthographic view, length centered along x-axis)
-> cross sections: 

Ask Claude to help:
(suggest py file naming needs to be updated to have these naming conventions)
+slast_uHJh_xs.py ->    xs_0_heel
+slast_heel_0.py  ->    xs_1_heel
+slast_heel_1.py  ->    xs_2_heel
    xs_3_crown
    xs_4_2_high_instep
+slast_instep.py    xs_5_instep
    xs_6_waist
    xs_7_joint
    xs_8_1st_MTP_joint
    xs_9_foot_length
+ last_profile.py has 2 functions, def rotate_vector( and def intersect_lines(, 
    that could be moved to helper_funcs.py, they're usages in other py files would 
    need to be updated





-rw-rw-r-- 1 rgrabbe rgrabbe 7976 Apr 17 20:21 slast_joint_xs.py

-rw-rw-r-- 1 rgrabbe rgrabbe 8352 Apr 17 20:21 slast_waist.py


common geometry to all files (suggest py file internal nameing needs updating to these conventions)
    -> placement transformation matrix,  local xy plane to 3d model placements (Transformation Matrix assemblies)
            (needs to highlight geometric components of insole and profile used to locate translation vector and rotation matrix)
    -> model lengths ( named *_lens), based on George Koleff's shoelast making geometries and namings
    -> euclidean points, ( named *_layout?) local xy plane reference points
    -> line wireframes,  local xy plane reference line drawing
    -> bsplines (to be done) local xy plane reference to be used with camera images made cross sections

Nurbs surface modeling from which 3d solids generated with FreeCAD 

Last hinge/crown release-mechanism construction


Camera images of shoe last using laser lines to generate cross section
point lines and point clouds using intelisense camera


[1] "Uppermaking for Bespoke and Orthopedic Shoemakers", Harmut & Dustin Seidich, Translated by Kevin Leahy. 
Edition 2024. Self published.

[2] "The Manufacture of Boots and Shoes: Being a Modern Treatis of All the Processes of Making and Manufacturing Footgear", Forgotten Books, 
2015. F.D. Golding, pages 84-86.

[3] Last size tables show 1/4" increments in instep and joint measurements between widths and full sizes.





# --- Surface sampling resolution considerations: ----
# The sampling resolution will determine the closeness of fit for the last 
# surface to input curvature lines. For control point sampling resolution, 
# I am now guessing 10 mm (had thought 20 to 30). 
# The cross section plane locations and
# orientations are set to mimic the foot structure, foot measurement locations, 
# orthoganal to last volumn, and least distorted cross section outline viewing,
# as being "better" for creating the shape than an arbitrary plane placement. I 
# haven't shown/seen this to be true, but this is how things have progressed. It
# may not be necessary and is hopefully not creating to much more work.

#----- Details on cross section control point locations as intersections with contour lines ----
# ----- Cross Section Control point position calculations ----
#xxxxxxxxxxxxxxxx
#   New interjection 5/28/2026,
#   Nurb pole (control point) locations are in the H,H1,H2,H3,T,T1,T2,C,C1,C2
# points sets along with planes xs_0...xs_8
# Each pole location is a function of the intersection of 3-surfaces.
# 1) The insole and last outlines in the xy plane project to the profiles H-J plane and J-B1
# extruded planes having normals of -y.
# The insole drawing has a center line curve, heel line curve, 
# C1 and C2 (not explicite yet) top view curves.
# 2) The profile gives the bottom , front-top, and heel curves. Also,
#   the medial and lateral highwater curves and C1 C2 (not explicit now) profile curves.
# 3)Cross sections provide the 3rd surface for intersections defining the points.
# 4)At the toe end, the front profile, last outline, and profile curves C,C1,C2,
#   T1,T2 provide the 2nd to final toe-end poles that are not constrained 
#   to a xs_x plane but only constrained by those surface intersections

bc_   -> Bspline Curve
bc_3d_front      
vertical constraint      , horizontal constriant , longitudinal constrains (by cross sections)  
bc_3d_front_top          , Center_line,C                    
bc_3d_bottom             , Center_line , H3              
bc_3d_medial_highwater   , bc_medial_last_outline,T1
bc_3d_lateral_highwater  , bc_lateral_last_outline,T2  
bc_3d_bottom             , insole_bc_medial,H1          
bc_3d_bottom             , insole_bc_lateral,H2        
bc_3d_medial_crown       , C1_insole_medial^1,C1
bc_3d_lateral_crown      , C2_insole_lateral^1,C2       

curve constraints that terminate in single point
insole_bc_medial,insole_bc_center,insole_bc_lateral
bc_medial_last_outline, bc_lasteral_last_outline

cross section point list
Cntrl Pt Medial ,  mid pt,    Cntrl Pt Lateral , End Termination
H1              , H H3   ,   H2 , Heel cup
T1              , T      ,   T2 , Toe patch
C1              , C      ,   C2 , Toe patch



^1 - new contrants

# ,  pole     ,   x-constraint  ,z-constraint  ,     y-constraint             
# , pole name ,   surface 1     ,   surface 2  ,           surface 3          
# , k=0-8     ,                 ,              ,                                    
# ,  H3 ,               xs_k ,            bc_3d_bottom      ,        center line              
# ,  H  ,               xs_k ,            bc_3d_bottom + 3mm,       center line              
# ,  H1 ,               xs_k ,            bc_3d_bottom + 3mm,                insole_bc_medial          H
# ,  H2 ,               xs_k ,            bc_3d_bottom + 3mm,              insole_bc_lateral         H
# ,  T1 ,               xs_k ,            bc_3d_medial_highwater,  bc_medial_last_outline   
# ,  T2 ,               xs_k ,            bc_3d_lateral_highwater,  bc_lateral_last_outline  
# ,  C  ,               xs_k ,            bc_3d_front_top ,  center line              
# ,  C1 ,               xs_k ,            C1_profile        ,  C1_insole                
# ,  C2 ,               xs_k ,            C2_profile        ,  C2_insole                


#   2nd to end floating (no xs plane)
#   pole       x-constraint  z-constraint             y-constraint              
#   pole name  surface 1     surface 2                surface 3                  
#   H          B1            B1+ nZ*3mm               center line                  
#   H3         Bl            B1+ nZ*3mm               center line                                    
#   H1                       bc_3d_bottom             insole_bc_medial         
#   H2         xs_k          bc_3d_bottom             insole_bc_lateral        
#   T1         xs_k          bc_3d_medial_highwater   bc_medial_last_outline   
#   T2         xs_k          bc_3d_lateral_highwater  bc_lateral_last_outline  
#   C          xs_k          bc_3d_front_top          center line              
#   C1         xs_k          C1_profile               C1_insole                
#   C2         xs_k          C2_profile               C2_insole                

*******************************************


#, At Toe end, _,                       ,                       ,                          ,                                                               
#,   H3         ,           B1+3mm*nZ   ,    _bc_3d_bottom, center line              ,
#,   H          ,           B1+3mm*nZ   ,          bc_3d_bottom+ 3mm,       center line        ,      
#,   H1         ,           xs_k        ,    bc_3d_bottom,  insole_bc_medial        ,  H
#,   H2         ,           xs_k        ,    bc_3d_bottom,  insole_bc_lateral       ,  H
#,   T1         ,           xs_k        ,     bc_3d_medial_highwater,  bc_medial_last_outline  , 
#,   T2         ,           xs_k        ,     bc_3d_lateral_highwater,  bc_lateral_last_outline , 
#,   C          ,           xs_k        ,     bc_3d_front_top ,  center line             , 
#,   C1         ,           xs_k        ,     C1_profile        ,  C1_insole               , 
#,   C2         ,           xs_k        ,     C2_profile        ,  C2_insole               , 








#xxxxxxxxxxxxxxxxxx
# Points are to be found as plane intersecions 
# with an insole and profile contour pair.
# Intersections are in global coordinates and will map back to local.
# First elevation is deterimined from
# cross section xs-plane's intersection with it's profile contour line (call it pt_pc), then the horizontal
# posiition as an intersection with it's contour line in the insole sketch with another appropriate plane.
# Propose appropriate plane: 
# The "projection of pt_pc onto J->H line" distance taken back along  J->C would give a pt_i.
# A plane defined by pt_pc, pt_i, containing the global y-axis would be be the plane to intersect
# the contour line with to obatain the horizontal position. 
# The horizontal and  verticle intersections give the coorditate of the control point.
#
# ---- Projection complexity note ----
# Each xs cutting plane has a unique orientation (normal not aligned with global axes), so
# "height" (HC) cannot be read as a simple global-Z difference.
# The correct approach:
#   1. Transform profile BSpline poles to global 3D via sketch_profile.Placement.multVec()
#   2. Intersect the 3D BSpline with Part.Plane(xs_N_placement.Base, xs_N_cutting_normal)
#      using hf.get_bspline_plane_intersection_new()
#   3. Project the result onto the sketch local-Y direction via dot product:
#        HC = (g_C - xs_N_placement.Base).dot(local_Y_direction)
#      local-Y per section:
#        xs_0/xs_1: gvec_uHC5  (perpendicular to H->B, toward C5)
#        xs_3/xs_4: gvec_K_I   (K -> instep midpoint direction)
#        xs_5:      gvec_J1_J  (J -> J1 direction)
# Using raw Length instead of the dot product gives wrong HC whenever the
# intersection point is not directly "above" the section center in the local frame.

# Cross section control point naming follows George Koeleff's book
# Top to bottom, median on left , lateral on right follow
#     C1 C C2,  C points are conincident with  top_bc and front_bc profile outlines. 
#     |     |,  For now C1 C2 are +12 and -12 mm (global y) offset from C at same height as C
#     |     |,  (Future add top and side contours for C1 and C2.)
#     |     |.  
#     T1 T T2,  T on heel outline, T1 and t2 on on medial_highwate_bc, and lateral_highwater_bc.
#     |      |, Insole last outline for width but use H1->J1 and H2->J2 in that area. 
#     |      |   (Need to add last outline in insole drawing instead of using insole H1->J1 and H2->J2.)
#     H1 H H2
#        H3
#
# ---- If extra sampling needed (plan B): that maintains a sortable order ----
# Cross section names can be inserted before xs_0 as xs__5, 
# and after say xs_5 as xs_55, implementing a decimal system.

# Similarly for Heel sections, but not as neatly 
# Keeping odd on the medial, even on lateral side,
# subsequent insertions can be implented as for cross section sampling.


# profile heel_bc outline control points will have C1,C,C2 coincident at b heel_bc,
# T1 T2 coincident with highwater bc ends
# H1 H3 H2 coincident with H at heel_bc

# profile top_bc control points termination at toe tip at end of C contour


# NOTES on cross-section stations:
# xs_0: first heel section
# xs_1: second heel section # xs_2 K1 to crown, normal to K1->E
# xs_3 instep: 1/2 of J1-H1
# xs_4 waist: 1/2 between joint cross section and the instep cross section
#  on line J->E, same normal as instep
# xs_5 joint: at profile J (= local origin = insole J in 3D)
# xs_6 1/3 of J->B1 (toe cap line), located on J->B1 line and perpendicular to J->B1 and in x-z plane 
# xs_7 2/3 of J->B1 
# xs_8 end of toes (foot length)
                                                                                                                   
(The following is in progress.)
Conceptual Design Notes: R. Grabbe                                    E                                            
                                                        _______________     H1                                     
                                               ________/               \_______                                    
                                              |                           __|  \__                                 
                                              |                       ___/        \__                               
                                             /                    ___/               \_                             
                                  H          |                 __/                     \__                          
                                  e          |             ___/                           \__ J1                    
                                  e          |          __/                                  \____________________ 
                                  l           \     ___/                                                         |  Last
                                              | ___/                                                             |  Toe
                                              |/                         ________                                |
                                             H|_________________________/        \_______________________________|
                                                                                       J
Conceptual Design Notes: R. Grabbe 
A Last creates a "cage" built by the H->H1->J1->J->H polygon that holds the foot 
into the heel of the shoe so it doesn't slide forward during a stride except for arch length extension.
The cage's  outline, more verbosely, is the line from the Heel (H), to the short heel point (H1),
down the instep to the top of the joint (J1) down to the bottom of the joint (J) and back to the heel along the the
bottom curve of the last (bottom_bc - bottom BSplineCurve) that holds the foot. 

The top of the line from H1 down to J1 is later hand drawn-in to show a crown on top of the instep
(a 1/8" crown bulge at mid J1-H1 xs_3), a slight convexity (centered at waist xs_4), finishing at J1 (xs_5). 

My insight is that, from the crown shape of this region, all snugness of fit is accomplished with the bottom shape
of the last pressing the foot up into the crown, the fit being tighter along the plantar tread of the foot.
The plantar tread of the foot is accustomed to holding weight. 
The curved shape
last have from J1 to H accomdates this. Salvatore Ferragammo talks about this in the 4th paragraph on page 69 in his book. "The foot
in a shoe is supported by the thins sliver along the lateral side of the plantar surface of the foot when standing. This
support follows down along vertical line through the ankle downto this portion of the foot."  I think, like setting your foot on a 
volley ball so only this portion is supported and the heel an ball are suspended in air. With your
foot on a volley ball, tilt it forward as if in a 3" 12 cm heel, it supports your foot without bearing on ball or heel.
This area pressing your
foot into the instep slope held by heel and ball girths keeps the foot from slidding into the shoe. Although, the arch
streaches in length on each step and your toes move forward 8-12 mm on each stride. Hence, shoes that are 12 - 18 mm longer
depending on usage.

The shape of this cage, using a 37-degree angle from H-B to H-H1, J dropping down to the ground and j1 

The intuitions G. Koleff uses to size the widths and heights of these regions are held precedent. as it is
a full inch / 25.4 mm larger in perimeter than the joint's girth. This size adequacy is shown next.

Extending the last above J1 allows the foot to slip forward in the shoe. 
For a girth of 11", here are the calculations.
                                                     < 1.33" ><    2.67"   >
xs_5           +----------------------+                     +-------+   
               |perimeter = 12.5"     |              +------+   ^   +----+       Circumference = 11.139"
 J1 = 55.9 mm  |          = 318 mm    |              | 1.5    2.2     1.0+--+
    = 2.2"     |                      |              |          v           |
               +----------------------+              +- --------------------+
                      W = 103 mm  = 4.05"                       4.05"
Joint Fit: for my foot, joint is 11" = 279.4 mm
    J1 height is calculated by Koleff as joint_girth / 5.0.
    J to J1 = 279.4/5 = 55.9
    Joint Width = 279.4/3 + 10mm = 103.1 mm
    Max size using rectangle: 2*103.1 + 2*55.9 = 318.1 mm = 12 4.2/8 " = 12.5", oversized by 1.5"

Thus the controlling size curves for this region are T1 C1 C=J1 C2 T2. Adjust these to follow the shape of the foot
across the joint, not changing J1 (C) location. To obtain the waist measurement, curve the bottom_bc up more behind the
ball of the foot xs_4, same with the instep xs_3. And follow back to xs_2 similarly, but maintain xs_1 and xs_0's bottom
heights.


Termination of insole control curves:
insole
Toe shape:

The insole shape and front_top_curve shape the last's toe area. Use the insole shape to make round, square, french,
or different points by extending it forward by 4 to 8 mm.
The top curve  front_top_bc shape the toe's sloping profile down to the insole tip  and are the only curve that terminates on the insole's tip. 
All others are trimmed to and terminate into the toe-end patch. 

                (Right)Front view;                                      (Front) Lateral side view of toe patch
                        Toe Patch                                             Toe Patch
                                                                                         
                             C                                                           
                             |                                                           
                             |                                              C     ------  
                             |                                                          \  
  L      C2 -----------+-----+----+----------- C1   M                    C1,C2     --------
  a                    |     |    |                 e                                      \
  t      T2 -----------+     |    +----------- T1   d                    T1,T2     ---------\ 
  e                    |     |    |                 i                                        |    
  r                    |     |    |                 a                                        | 
  a                    |     |    |                 l                                         \
  l                    |     |    |                                                           |
                       |     |    |                                                           |
                       |     |    |                                                           |
         H2------------+-----+----+----------- H1                         H1,H2     ----------+
                             |
                             H

In FreeCAD 3d view, move the view cube in upper left corner of display to "Right" for Front view.
                            '          '                               to "Front" to see Lateral side view.











Clipboard
I coin the verticle line intersecting the ankle












