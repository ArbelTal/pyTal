from pyrevit import revit, forms
from Autodesk.Revit.DB import FilteredElementCollector, ImportInstance

# Initialize Document and UIDocument
uidoc = __revit__.ActiveUIDocument
doc = uidoc.Document
view = doc.ActiveView

# Collect all DWG import instances in the current view
dwg_instances = FilteredElementCollector(doc, view.Id).OfClass(ImportInstance).ToElements()

# Check if any DWG instances are found
if not dwg_instances:
    forms.alert("No DWG imports or links found in the current view.", title="DWG Selector")
else:
    # Prepare a dictionary for selection with element names or IDs
    dwg_options = {}
    for dwg in dwg_instances:
        name = dwg.Name  # DWG name
        element_id = dwg.Id.IntegerValue
        dwg_options["{} (ID: {})".format(name, element_id)] = dwg

    # Let user select one or more DWGs
    selected_dwgs = forms.SelectFromList.show(
        sorted(dwg_options.keys()),
        multiselect=True,
        title="Select DWG Imports or Links",
        instructions="Select one or more DWG elements to proceed."
    )

    if selected_dwgs:
        # Highlight selected DWGs
        with revit.Transaction("Select DWG Imports"):
            selected_ids = [dwg_options[sel].Id for sel in selected_dwgs]
            uidoc.Selection.SetElementIds(selected_ids)
            print("Selected DWGs: {}".format(", ".join(selected_dwgs)))
    else:
        forms.alert("No DWG selected.", title="DWG Selector")
