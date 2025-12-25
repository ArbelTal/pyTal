# -*- coding: utf-8 -*-
from pyrevit import forms
from Autodesk.Revit.DB import (
    FilteredElementCollector,
    BuiltInCategory,
    Wall,
    Transaction,
    Line,
    ReferenceArray,
    Dimension,
    RevitLinkInstance,
    Options,
    Reference,
    PlanarFace,
    FamilyInstance,
    FamilyInstanceReferenceType,
    XYZ,
    HostObjectUtils, 
    ShellLayerType, 
    HostObject,
    TransactionStatus,
    ElementId,
    LocationCurve
)
from Autodesk.Revit.UI.Selection import ObjectType, ISelectionFilter
from Autodesk.Revit.Exceptions import OperationCanceledException

# Get the active document and view
uidoc = __revit__.ActiveUIDocument
if not uidoc:
    forms.alert("No active Revit document.")
    raise SystemExit
doc = uidoc.Document
current_view = uidoc.ActiveView

# ---------------------------------------------------------------------------
# Filters
# ---------------------------------------------------------------------------
class FamilySelectionFilter(ISelectionFilter):
    def AllowElement(self, elem):
        return isinstance(elem, FamilyInstance)
        
    def AllowReference(self, reference, position):
        return False

class WallOrLinkSelectionFilter(ISelectionFilter):
    def AllowElement(self, elem):
        # Allow Walls or Links
        if isinstance(elem, Wall):
            return True
        if isinstance(elem, RevitLinkInstance):
            return True
        return False
        
    def AllowReference(self, reference, position):
        return True



# ---------------------------------------------------------------------------
# Selection Logic
# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def get_family_center_ref(fam_inst):
    # Try Left/Right first
    refs = fam_inst.GetReferences(FamilyInstanceReferenceType.CenterLeftRight)
    if refs: return refs[0]
    # Try Front/Back
    refs = fam_inst.GetReferences(FamilyInstanceReferenceType.CenterFrontBack)
    if refs: return refs[0]
    return None

def get_best_wall_face_ref(target_wall, link_instance, source_pt, doc_context):
    """
    Finds the face of the wall closest to source_pt.
    Returns a Reference valid for Dimensioning (LinkRef if needed).
    """
    # Get Side Faces (Exterior and Interior)
    # The references returned are geometric references.
    try:
        refs_ext = HostObjectUtils.GetSideFaces(target_wall, ShellLayerType.Exterior)
        refs_int = HostObjectUtils.GetSideFaces(target_wall, ShellLayerType.Interior)
    except Exception:
        # Not a HostObject (e.g. In-Place Wall maybe?)
        return None
        
    all_refs = list(refs_ext) + list(refs_int)
    if not all_refs:
        return None
        
    best_ref = None
    min_dist = float('inf')
    
    # Transform Family Point to Local if needed
    check_pt = source_pt # Default Host
    if link_instance:
        transform = link_instance.GetTransform()
        check_pt = transform.Inverse.OfPoint(source_pt)
    
    for ref in all_refs:
        # Get Geometry 
        # Note: If Link, we assume GetGeometryObject works on the Local Link Doc 
        # using the Local Ref.
        geom_obj = None
        try:
             # If target_wall is in Link, we must use LinkDoc
             if link_instance:
                  geom_obj = target_wall.Document.GetElement(target_wall.Id).GetGeometryObjectFromReference(ref)
             else:
                  geom_obj = target_wall.GetGeometryObjectFromReference(ref)
        except:
             pass
             
        if geom_obj and hasattr(geom_obj, "Project"):
             res = geom_obj.Project(check_pt)
             if res:
                  if res.Distance < min_dist:
                       min_dist = res.Distance
                       best_ref = ref
    
    # Fallback
    if not best_ref and all_refs:
        best_ref = all_refs[0]
        
    if not best_ref:
        return None
        
    # Create Link Reference if needed
    if link_instance:
        return best_ref.CreateLinkReference(link_instance)
    else:
        return best_ref

# ---------------------------------------------------------------------------
# Processing Loop
# ---------------------------------------------------------------------------
while True:
    try:
        # 1. Select Family
        try:
            fam_ref = uidoc.Selection.PickObject(
                ObjectType.Element, 
                FamilySelectionFilter(), 
                "Select a Family Instance (ESC to Finish Script)"
            )
        except OperationCanceledException:
            # User cancelled at start -> Exit Script
            break
            
        selected_family = doc.GetElement(fam_ref.ElementId)
        
        # 2. Select Wall
        try:
            wall_ref_pick = uidoc.Selection.PickObject(
                ObjectType.PointOnElement,
                WallOrLinkSelectionFilter(),
                "Select a Wall (Host or Link) (ESC to Restart Selection)"
            )
        except OperationCanceledException:
            # User cancelled wall pick -> Go back to Family selection
            continue

        # Process Selection
        target_wall = None
        link_inst = None
        elem = doc.GetElement(wall_ref_pick.ElementId)

        if isinstance(elem, Wall):
            target_wall = elem
        elif isinstance(elem, RevitLinkInstance):
            link_inst = elem
            if wall_ref_pick.LinkedElementId == ElementId.InvalidElementId:
                print("Invalid Link Selection.")
                continue
                
            link_doc = link_inst.GetLinkDocument()
            if not link_doc:
                 print("Link Doc unavailable.")
                 continue
                 
            linked_element = link_doc.GetElement(wall_ref_pick.LinkedElementId)
            if isinstance(linked_element, Wall):
                target_wall = linked_element
            else:
                print("Not a Wall.")
                continue
        else:
            print("Not a Wall.")
            continue

        # Get Family Point (Source)
        pt_fam = None
        loc = selected_family.Location
        if hasattr(loc, 'Point'):
            pt_fam = loc.Point
        else:
            print("Family has no point.")
            continue

        # Get References
        ref1 = get_family_center_ref(selected_family)
        if not ref1:
            print("No Center Ref.")
            continue

        ref2 = get_best_wall_face_ref(target_wall, link_inst, pt_fam, doc)
        if not ref2:
            print("No Valid Wall Face found.")
            continue

        # Geometry Calculation
        # Project Family Point to Wall to find roughly perpendicular endpoint
        res_pt = None # Placeholder
        if link_inst:
             # Local Wall
             t_inv = link_inst.GetTransform().Inverse
             pt_fam_local = t_inv.OfPoint(pt_fam)
             w_curve = target_wall.Location.Curve
             res_inter = w_curve.Project(pt_fam_local)
             if res_inter:
                 res_pt_local = res_inter.XYZPoint
                 res_pt = link_inst.GetTransform().OfPoint(res_pt_local)
        else:
             # Host Wall
             w_curve = target_wall.Location.Curve
             res_inter = w_curve.Project(pt_fam)
             if res_inter:
                 res_pt = res_inter.XYZPoint
        
        if not res_pt:
             print("Could not project point.")
             continue

        # 3. Smart Placement (Single Click)
        # We ask for a Point.
        # If the point is ON an existing Dimension, we align.
        # If not, we place manually at that point.
        
        try:
            place_pt = uidoc.Selection.PickPoint("Click to Place Dimension (or Click on existing Dimension to Align) (ESC to Restart)")
        except OperationCanceledException:
             continue # Restart loop
             
        # Check for Alignment
        # Strategy: Find all Dimensions in View. Check distance from place_pt to their line.
        
        dim_line = None
        alignment_found = False
        
        # Performance: Maybe limit collector?
        # But Dimensions in view usually aren't that many.
        visible_dims = FilteredElementCollector(doc, current_view.Id).OfClass(Dimension).ToElements()
        
        # Tolerance for "Clicking on a dimension" 
        # 0.5 feet is generous but safer for "empty space" clicks. 
        # Maybe 0.2 feet (~60mm)?
        TOLERANCE_ALIGN = 0.5 
        
        # Helper projector
        def project_to_line_infinite(pt, origin, direction):
            vec = pt - origin
            dist = vec.DotProduct(direction)
            return origin.Add(direction.Multiply(dist))

        # Flatten Place Point for Check
        view_z = pt_fam.Z
        if current_view.GenLevel:
             view_z = current_view.GenLevel.Elevation
        place_pt_check = XYZ(place_pt.X, place_pt.Y, view_z)

        best_dist = float('inf')
        best_dim_curve = None
        
        for d in visible_dims:
             # Check if linear
             try:
                 c = d.Curve
                 if isinstance(c, Line):
                      # Check distance to infinite line
                      # Dist = |(P - Origin) x Dir| / |Dir| (Dir is unit)
                      # or just project and measure
                      
                      # Flatten Dim Line
                      d_orig = c.Origin
                      d_dir = c.Direction
                      
                      flat_orig = XYZ(d_orig.X, d_orig.Y, view_z)
                      flat_dir = XYZ(d_dir.X, d_dir.Y, 0)
                      if flat_dir.IsZeroLength(): continue
                      flat_dir = flat_dir.Normalize()
                      
                      proj = project_to_line_infinite(place_pt_check, flat_orig, flat_dir)
                      dist = place_pt_check.DistanceTo(proj)
                      
                      # Also check if "along" the segment? 
                      # User says "pick existing dimension". 
                      # Usually means clicking near it. 
                      # We won't restrict to the finite segment length to allow extending alignment.
                      
                      if dist < TOLERANCE_ALIGN and dist < best_dist:
                           best_dist = dist
                           best_dim_curve = (flat_orig, flat_dir)
                           alignment_found = True
             except:
                 pass
        
        if alignment_found and best_dim_curve:
             # Align!
             print("Aligning to existing Dimension...")
             flat_orig, flat_dir = best_dim_curve
             
             # Project measure points to this line
             flat_pt1 = XYZ(pt_fam.X, pt_fam.Y, view_z)
             flat_pt2 = XYZ(res_pt.X, res_pt.Y, view_z)
             
             proj_pt1 = project_to_line_infinite(flat_pt1, flat_orig, flat_dir)
             proj_pt2 = project_to_line_infinite(flat_pt2, flat_orig, flat_dir)
             
             dim_line = Line.CreateBound(proj_pt1, proj_pt2)

        else:
             # Manual Placement (Perpendicular)
             # Use place_pt_check which is already flattened
             
            # Determine Direction (Wall Normal)
            dim_dir = None
            if target_wall and isinstance(target_wall.Location, LocationCurve):
                 curve = target_wall.Location.Curve
                 if isinstance(curve, Line):
                      wall_dir = curve.Direction
                      dim_dir = XYZ(-wall_dir.Y, wall_dir.X, 0)
            
            if not dim_dir:
                 vec_diff = (res_pt - pt_fam)
                 if not vec_diff.IsZeroLength():
                      dim_dir = vec_diff.Normalize()
            if not dim_dir:
                 dim_dir = XYZ.BasisX
                 
            dim_line_end = place_pt_check.Add(dim_dir)
            dim_line = Line.CreateBound(place_pt_check, dim_line_end)

        ref_array = ReferenceArray()
        ref_array.Append(ref1)
        ref_array.Append(ref2)



        t = Transaction(doc, "Auto Dimension ManualLoop")
        t.Start()
        try:
            dim = doc.Create.NewDimension(current_view, dim_line, ref_array)
            t.Commit()
        except Exception as e:
            t.RollBack()
            # print("Failed to create dimension: {}".format(e))
            # Try 5 degrees rotation fallback? Sometimes perfectly orthogonal causes issues if refs are slightly off?
            # No, usually Strict Orthogonality is what it wants.
            print("Failed: {}".format(e))
            
    except Exception as e:
        print("Error in loop: {}".format(e))
        break
