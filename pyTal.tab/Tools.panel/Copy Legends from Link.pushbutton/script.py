"""Copy Legends From Link"""
# -*- coding: utf-8 -*-
__title__ = "Copy Legends\nFrom Link"
__doc__ = """Version = 1.0
Date    = 13.01.2025
________________________________________________________________
Description:
Select link from list to copy legends from.
________________________________________________________________
Last Updates:
- [13.01.2025] v1.0 Change Description
________________________________________________________________
Author: Arbel Tal"""

import clr
from System.Collections.Generic import List

# Import pyRevit forms
from pyrevit import forms

# Import Revit API
clr.AddReference('RevitAPI')
clr.AddReference('RevitAPIUI')
from Autodesk.Revit.DB import (
    FilteredElementCollector, ViewType, Transaction,
    ElementId, ViewDuplicateOption, View, RevitLinkInstance,
    CopyPasteOptions, ElementTransformUtils
)

doc = __revit__.ActiveUIDocument.Document
uidoc = __revit__.ActiveUIDocument

# Get all Revit links in the current document
links = FilteredElementCollector(doc)\
    .OfClass(RevitLinkInstance)\
    .ToElements()

# Create dictionary of link names and their documents
link_dict = {}
for link in links:
    if link.GetLinkDocument():  # Only include loaded links
        link_name = link.GetLinkDocument().Title
        link_dict[link_name] = link.GetLinkDocument()

if not link_dict:
    forms.alert("No loaded Revit links found in current document", exitscript=True)

# Calculate form size based on number of links and longest name
num_links = len(link_dict)
min_height = 100  # Minimum height
min_width = 300   # Minimum width
height_per_item = 30  # Height per link item
width_per_char = 8    # Approximate width per character

# Calculate heights
form_height = max(min_height, min(400, num_links * height_per_item + 80))

# Calculate width based on longest link name
max_link_length = max(len(name) for name in link_dict.keys())
form_width = max(min_width, min(800, max_link_length * width_per_char + 100))  # Add padding and cap at 800px

# Show link selector form using pyRevit forms with adjusted size
selected_link_name = forms.SelectFromList.show(
    sorted(link_dict.keys()),
    title='Select Revit Link',
    button_name='Select Link',
    multiselect=False,
    width=form_width,
    height=form_height
)

if not selected_link_name:
    forms.alert("No link was selected", exitscript=True)

link_doc = link_dict[selected_link_name]

# Get legends from selected link
legends = FilteredElementCollector(link_doc)\
    .OfClass(View)\
    .WhereElementIsNotElementType()\
    .ToElements()

# Create dictionary of legend names and elements
legend_dict = {legend.Name: legend for legend in legends 
              if legend.ViewType == ViewType.Legend}

if not legend_dict:
    forms.alert("No legends found in selected link", exitscript=True)

# Calculate form size for legends based on number and longest name
num_legends = len(legend_dict)
legend_form_height = max(min_height, min(600, num_legends * height_per_item + 80))

# Calculate width based on longest legend name
max_legend_length = max(len(name) for name in legend_dict.keys())
legend_form_width = max(min_width, min(800, max_legend_length * width_per_char + 100))

# Show legend selector form using pyRevit forms
selected_legend_names = forms.SelectFromList.show(
    sorted(legend_dict.keys()),
    title='Select Legends to Copy',
    button_name='Copy Selected',
    multiselect=True,
    width=legend_form_width,
    height=legend_form_height
)

if not selected_legend_names:
    forms.alert("No legends selected", exitscript=True)

# Get selected legend elements
selected_legends = [legend_dict[name] for name in selected_legend_names]

# Copy selected legends
t = Transaction(doc, "Copy Legends from Link")
t.Start()

# Create copy/paste options
copy_options = CopyPasteOptions()

for legend in selected_legends:
    # Create a list of element ids to copy
    element_list = List[ElementId]([legend.Id])
    
    # Copy the legend from link to current document
    ElementTransformUtils.CopyElements(
        link_doc,           # source document
        element_list,       # elements to copy
        doc,               # destination document
        None,              # no transform needed
        copy_options
    )
    print("Copied legend: " + legend.Name)

t.Commit()
