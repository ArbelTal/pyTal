"""Create Filled Region"""
# -*- coding: utf-8 -*-
__title__ = "Create\nFilled Region"
__doc__ = """Version = 1.0
Date    = 31.12.2024
________________________________________________________________
Description:
Create filled region from selected closed polygon.
1. select detail lines that forms closed polygon. 
2. delete the detail lines.
________________________________________________________________
Last Updates:
- [31.12.2024] v1.0 Change Description
________________________________________________________________
Author: Arbel Tal"""

from Autodesk.Revit.DB import *
from Autodesk.Revit.UI import TaskDialog
from Autodesk.Revit.UI.Selection import ObjectType
from Autodesk.Revit.Exceptions import InvalidOperationException
import clr

# Access the Revit application and document
uiapp = __revit__
uidoc = uiapp.ActiveUIDocument

if not uidoc:
    TaskDialog.Show("Error", "No active document. Please open a Revit project and try again.")
    raise Exception("No ActiveUIDocument found.")

doc = uidoc.Document


# Function to compare points with a tolerance
def points_are_equal(point1, point2, tolerance=1e-6):
    return abs(point1.X - point2.X) < tolerance and \
        abs(point1.Y - point2.Y) < tolerance and \
        abs(point1.Z - point2.Z) < tolerance


# Prompt the user to select detail lines
def select_detail_lines():
    try:
        sel = uidoc.Selection.PickObjects(ObjectType.Element, "Select detail lines to form a closed polygon.")
        return [doc.GetElement(ref) for ref in sel]
    except InvalidOperationException:
        return None


# Check if the selected detail lines form a closed polygon
def is_closed_polygon(detail_lines):
    endpoints = []
    for line in detail_lines:
        curve = line.GeometryCurve
        endpoints.append((curve.GetEndPoint(0), curve.GetEndPoint(1)))

    # Check if endpoints match with tolerance
    start_to_end = {start: end for start, end in endpoints}
    start_point = endpoints[0][0]
    current_point = start_point
    for _ in range(len(endpoints)):
        found_match = False
        for start, end in start_to_end.items():
            if points_are_equal(current_point, start):
                current_point = end
                found_match = True
                break
        if not found_match:
            return False
    return points_are_equal(current_point, start_point)


# Create a filled region from the closed polygon
def create_filled_region(detail_lines):
    filled_region_type = FilteredElementCollector(doc).OfClass(FilledRegionType).FirstElement()
    if not filled_region_type:
        TaskDialog.Show("Error", "No filled region type found in the project.")
        return None

    try:
        with Transaction(doc, "Create Filled Region") as t:
            t.Start()

            # Create a CurveLoop instead of CurveArray
            curves = [line.GeometryCurve for line in detail_lines]
            curve_loop = CurveLoop()
            for curve in curves:
                curve_loop.Append(curve)

            view = doc.ActiveView
            filled_region = FilledRegion.Create(doc, filled_region_type.Id, view.Id,
                                                [curve_loop])  # Pass a list of CurveLoop

            t.Commit()
            return filled_region

    except Exception as e:
        TaskDialog.Show("Error", str(e))
        return None


# Delete the selected detail lines
def delete_detail_lines(detail_lines):
    try:
        with Transaction(doc, "Delete Detail Lines") as t:
            t.Start()

            for line in detail_lines:
                doc.Delete(line.Id)

            t.Commit()

    except Exception as e:
        TaskDialog.Show("Error", str(e))


# Main execution
selected_lines = select_detail_lines()
if selected_lines:
    if is_closed_polygon(selected_lines):
        filled_region = create_filled_region(selected_lines)
        if filled_region:
            delete_detail_lines(selected_lines)
            TaskDialog.Show("Success", "Filled region created, and detail lines deleted.")
    else:
        TaskDialog.Show("Error", "Selected detail lines do not form a closed polygon.")
else:
    TaskDialog.Show("Cancelled", "No detail lines selected.")
