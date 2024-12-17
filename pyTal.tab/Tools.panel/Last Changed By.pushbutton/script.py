# -*- coding: utf-8 -*-
__title__   = "Last Change by"
__doc__ = """Version = 1.5
Date    = 17.12.2024
_____________________________________________________________________
Description:
Select all elements last changed by the selected user. 
Assigns unique colors to users temporarily, shows them in the form, and resets graphics after selection.
_____________________________________________________________________
How-To:
- Click the Button
_____________________________________________________________________
Last update:
- [17.12.2024] - V1.5: Removed RGB values in the form display.
_____________________________________________________________________
Author: Arbel Tal"""


# ╦╔╦╗╔═╗╔═╗╦═╗╔╦╗╔═╗
# ║║║║╠═╝║ ║╠╦╝ ║ ╚═╗
# ╩╩ ╩╩  ╚═╝╩╚═ ╩ ╚═╝ IMPORTS
#====================================================================================================

from Autodesk.Revit.DB import *
from pyrevit import forms

import clr
clr.AddReference('System')
from System.Collections.Generic import List
from collections import defaultdict

import random

# ╦  ╦╔═╗╦═╗╦╔═╗╔╗ ╦  ╔═╗╔═╗
# ╚╗╔╝╠═╣╠╦╝║╠═╣╠╩╗║  ║╣ ╚═╗
#  ╚╝ ╩ ╩╩╚═╩╩ ╩╚═╝╩═╝╚═╝╚═╝ VARIABLES
#====================================================================================================

uidoc = __revit__.ActiveUIDocument
doc = __revit__.ActiveUIDocument.Document
active_view = doc.ActiveView

# ╔╦╗╔═╗╦╔╗╔
# ║║║╠═╣║║║║
# ╩ ╩╩ ╩╩╝╚╝ MAIN
#====================================================================================================

# 1 Get All Elements
elements = FilteredElementCollector(doc).WhereElementIsNotElementType() \
           .WhereElementIsViewIndependent() \
           .ToElements()

# 2 Sort Elements by User LastChangedBy
elements_sorted_by_last_user = defaultdict(list)
for el in elements:
    try:
        wti = WorksharingUtils.GetWorksharingTooltipInfo(doc, el.Id)
        last = wti.LastChangedBy
        if last and last.strip():  # Ignore empty or whitespace-only usernames
            elements_sorted_by_last_user[last].append(el.Id)
    except:
        pass

# 3 Assign Unique Colors to Users
def generate_random_color():
    return Color(random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))

user_colors = {user: generate_random_color() for user in elements_sorted_by_last_user.keys()}

# 4 Apply Temporary Color to Elements in a Transaction
override_settings = OverrideGraphicSettings()

t = Transaction(doc, "Assign User Colors")
t.Start()
try:
    for user, element_ids in elements_sorted_by_last_user.items():
        color = user_colors[user]
        override_settings.SetProjectionLineColor(color)
        override_settings.SetSurfaceForegroundPatternColor(color)
        for el_id in element_ids:
            active_view.SetElementOverrides(el_id, override_settings)
finally:
    t.Commit()

# 5 Show Form with Users
user_display = ["{0}".format(user) for user in elements_sorted_by_last_user.keys()]

selected_user_display = forms.SelectFromList.show(user_display, button_name='Select User')

# 6 Reset All Graphics and Keep Selected User's Elements Selected
reset_override = OverrideGraphicSettings()

t = Transaction(doc, "Reset Graphics and Keep Selection")
t.Start()
try:
    # Reset all graphics
    for el in elements:
        active_view.SetElementOverrides(el.Id, reset_override)

    if selected_user_display:
        # Extract the selected user and highlight elements
        selected_user = selected_user_display
        selected_element_ids = elements_sorted_by_last_user[selected_user]

        # Keep selected user's elements selected (without graphic overrides)
        List_new_selection = List[ElementId](selected_element_ids)
        uidoc.Selection.SetElementIds(List_new_selection)
finally:
    t.Commit()
