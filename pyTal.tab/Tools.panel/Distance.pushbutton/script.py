# -*- coding: utf-8 -*-
__title__   = "Distance"
__doc__ = """Version = 1.0
Date    = 23.12.2024
_____________________________________________________________________
Description:
Select 2 elements to calculate the distance between them (xyz). 
_____________________________________________________________________
How-To:
- Click the Button
_____________________________________________________________________
Last update:
- [23.12.2024] - V1.0: Select 2 elements to calculate the distance between them (xyz). 
_____________________________________________________________________
Author: Arbel Tal"""

from pyrevit import forms
from Autodesk.Revit.UI import Selection
from Autodesk.Revit.DB import XYZ, ElementId

# Conversion factor from feet to meters
FEET_TO_METERS = 0.3048

# Function to calculate distance in feet and convert to meters
def calculate_distance_in_meters(point1, point2):
    # Distance in X-Y plane
    xy_distance = ((point2.X - point1.X) ** 2 + (point2.Y - point1.Y) ** 2) ** 0.5
    # Difference in Z
    z_distance = abs(point2.Z - point1.Z)
    # Total distance in feet
    distance_in_feet = xy_distance + z_distance
    # Convert to meters
    return distance_in_feet * FEET_TO_METERS

# Get the current Revit document and UI application
uiapp = __revit__.ActiveUIDocument
doc = uiapp.Document
uidoc = uiapp.Application.ActiveUIDocument

try:
    # Prompt user to select two elements
    selected_refs = uidoc.Selection.PickObjects(
        Selection.ObjectType.Element,
        "Select exactly 2 elements to calculate the distance."
    )

    # Ensure exactly two elements are selected
    if not selected_refs or len(selected_refs) != 2:
        forms.alert("You must select exactly 2 elements. You selected {} elements.".format(len(selected_refs)))
    else:
        # Get the selected elements
        element1 = doc.GetElement(selected_refs[0].ElementId)
        element2 = doc.GetElement(selected_refs[1].ElementId)

        # Get the locations of the two elements
        location1 = element1.Location
        location2 = element2.Location

        # Check if both locations are valid
        if location1 and location2 and hasattr(location1, 'Point') and hasattr(location2, 'Point'):
            point1 = location1.Point
            point2 = location2.Point

            # Calculate the distance in meters
            distance_in_meters = calculate_distance_in_meters(point1, point2)

            # Display the distance to the user
            forms.alert("The distance between the selected items is: {:.2f} meters.".format(distance_in_meters))
        else:
            forms.alert("One or both selected elements do not have valid locations.")
except Exception as e:
    forms.alert("An error occurred: {}".format(e))
