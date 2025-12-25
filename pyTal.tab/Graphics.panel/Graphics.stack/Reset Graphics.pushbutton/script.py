"""Reset Graphics Overrides"""
# -*- coding: utf-8 -*-
__title__ = "Reset\nGraphics Overrides"
__doc__ = """Version = 1.0
Date    = 01.10.2024
________________________________________________________________
Description:
Create Worksets from CSV file. 
________________________________________________________________
Last Updates:
- [01.10.2024] v1.0 Change Description
________________________________________________________________
Author: Arbel Tal"""

from pyrevit import revit, DB

# Initialize document and active view
uidoc = __revit__.ActiveUIDocument
doc = uidoc.Document
active_view = uidoc.ActiveView

# Collect all elements in the current view
collector = DB.FilteredElementCollector(doc, active_view.Id)
elements_in_view = collector.WhereElementIsNotElementType().ToElements()

# Begin a transaction to reset graphics overrides
with revit.Transaction('Reset Graphics Overrides'):
    for element in elements_in_view:
        # Reset all graphics overrides in active view
        active_view.SetElementOverrides(element.Id, DB.OverrideGraphicSettings())
