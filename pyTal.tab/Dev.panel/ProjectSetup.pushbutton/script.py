# Import necessary modules
from pyrevit import revit, DB, forms
from Autodesk.Revit.UI.Selection import ObjectType
from System.Collections.Generic import List  # Import List from .NET collections

# Initialize the document and UI
uidoc = __revit__.ActiveUIDocument
doc = uidoc.Document

# Function to select a linked Revit model
def select_linked_model():
    sel = uidoc.Selection
    linked_model_reference = sel.PickObject(ObjectType.Element, "Select the linked Revit model")
    linked_model = doc.GetElement(linked_model_reference.ElementId)

    # Ensure the selected model is a linked model
    if not isinstance(linked_model, DB.RevitLinkInstance):
        forms.alert("Please select a valid linked Revit model.", exitscript=True)

    return linked_model

# Function to copy and pin levels and grids
def copy_and_pin_levels_grids(link_instance):
    # Get the linked document
    link_doc = link_instance.GetLinkDocument()
    if link_doc is None:
        forms.alert("The linked document is not available. Please select a valid linked model.", exitscript=True)

    # Get levels and grids from the linked model
    linked_levels = list(DB.FilteredElementCollector(link_doc).OfClass(DB.Level))
    linked_grids = list(DB.FilteredElementCollector(link_doc).OfClass(DB.Grid))

    if not linked_levels and not linked_grids:
        forms.alert("No levels or grids found in the selected linked model.", exitscript=True)

    # Prepare list of element IDs to copy
    level_ids = List[DB.ElementId]([level.Id for level in linked_levels])
    grid_ids = List[DB.ElementId]([grid.Id for grid in linked_grids])

    # Start a transaction for copying and pinning elements
    with revit.Transaction("Copy and Pin Levels and Grids"):
        # Copy levels
        copy_options = DB.CopyPasteOptions()
        transform = DB.Transform.Identity

        copied_level_ids = DB.ElementTransformUtils.CopyElements(link_doc, level_ids, doc, transform, copy_options)
        for new_level_id in copied_level_ids:
            new_level = doc.GetElement(new_level_id)
            new_level.Pinned = True  # Pin the copied level to simulate monitoring

        # Copy grids
        copied_grid_ids = DB.ElementTransformUtils.CopyElements(link_doc, grid_ids, doc, transform, copy_options)
        for new_grid_id in copied_grid_ids:
            new_grid = doc.GetElement(new_grid_id)
            new_grid.Pinned = True  # Pin the copied grid to simulate monitoring

# Main execution flow
with revit.TransactionGroup("Copy and Pin Levels and Grids"):
    # Step 1: Select the linked model
    linked_model = select_linked_model()

    # Step 2: Copy and pin levels and grids
    copy_and_pin_levels_grids(linked_model)
