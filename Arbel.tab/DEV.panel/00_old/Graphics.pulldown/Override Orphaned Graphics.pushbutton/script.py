import pyrevit
from pyrevit import revit, forms
from Autodesk.Revit.DB import FilteredElementCollector, OverrideGraphicSettings, Color, ElementId, Transaction, \
    FamilyInstance


def get_orphaned_elements(view, doc):
    """Gets all orphaned elements (unhosted) in the specified view."""
    # Collect all elements in the view
    elements_in_view = FilteredElementCollector(doc, view.Id).WhereElementIsNotElementType().ToElements()

    # Filter for hosted elements that have lost their host (i.e., orphaned elements)
    orphaned_elements = []
    for element in elements_in_view:
        if isinstance(element, FamilyInstance):
            # Check if the element is hosted and has no host (i.e., it is orphaned)
            if element.Host is None:
                orphaned_elements.append(element)

    # Debugging: Collect the orphaned element IDs
    orphaned_element_ids = [str(element.Id) for element in orphaned_elements]

    # Report orphaned elements in a pop-up window
    if orphaned_element_ids:
        forms.alert("Orphaned Element IDs:\n" + "\n".join(orphaned_element_ids), title="Orphaned Elements Report")
    else:
        forms.alert("No orphaned elements found in this view.", title="Orphaned Elements Report")

    return orphaned_elements


def override_element_graphics(element, doc, color, line_weight):
    """Overrides the graphics of the specified element with the given color and line weight."""
    override_settings = OverrideGraphicSettings()

    # Set the projection line color and weight (for 2D views)
    override_settings.SetProjectionLineColor(color)
    override_settings.SetProjectionLineWeight(line_weight)

    # Apply the override to the element in the active view
    doc.ActiveView.SetElementOverrides(element.Id, override_settings)


def override_orphaned_graphics(view, doc, color=Color(255, 0, 0), line_weight=2):
    """Overrides the graphics of all orphaned elements in the specified view with the given color and line weight."""
    orphaned_elements = get_orphaned_elements(view, doc)

    # Start a transaction to override graphics
    with Transaction(doc, "Override Orphaned Element Graphics") as t:
        t.Start()  # Start the transaction
        for element in orphaned_elements:
            override_element_graphics(element, doc, color, line_weight)
        t.Commit()  # Commit the transaction to apply the changes


def my_addin():
    doc = revit.doc
    view = revit.active_view

    # Define the override color (RGB red)
    color = Color(255, 0, 0)

    # Override orphaned elements in the view
    override_orphaned_graphics(view, doc, color)


# Run the main function
my_addin()
