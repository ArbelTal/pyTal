# -*- coding: utf-8 -*-
__title__   = "One Line Diagram"
__doc__     = """Version = 0.1
Date    = 29.09.2024
________________________________________________________________
Description:

This is the placeholder for a .pushbutton
You can use it to start your pyRevit Add-In

________________________________________________________________
How-To:

1. [Hold ALT + CLICK] on the button to open its source folder.
You will be able to override this placeholder.

2. Automate One Line Diagram ;)

________________________________________________________________
TODO:
[FEATURE] - Describe Your ToDo Tasks Here
________________________________________________________________
Last Updates:
- [29.09.2024] v0.1 Change Description 
________________________________________________________________
Author: Arbel Tal"""

# Import necessary modules from Revit API and pyRevit
from Autodesk.Revit.DB import (
    FilteredElementCollector,
    BuiltInCategory,
    Transaction,
    Line,
    XYZ,
    Plane,
    SketchPlane,
    ViewDrafting,
    ViewFamilyType,
    FamilySymbol,
    ElementId,
    TextNote,
    TextNoteType,
    ViewFamily,
    Level,
    TextNoteOptions
)
from Autodesk.Revit.UI import TaskDialog
from pyrevit import revit, forms
import math
import logging
import os

# Configure logging
LOG_FILENAME = os.path.join(forms.documents_path(), 'OneLineDiagram.log')
logging.basicConfig(
    filename=LOG_FILENAME,
    filemode='w',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Define default constants
DEFAULT_PANEL_PREFIX = 'SN_'
DEFAULT_VIEW_NAME = 'One-Line Diagram'
DEFAULT_SPACING_X = 20  # Base horizontal spacing
DEFAULT_SPACING_Y = 10  # Base vertical spacing

def get_electrical_panels(doc, prefix):
    """
    Collects all electrical panels in the document with the specified prefix.
    """
    try:
        panels = FilteredElementCollector(doc) \
            .OfCategory(BuiltInCategory.OST_ElectricalEquipment) \
            .WhereElementIsNotElementType() \
            .ToElements()
        filtered_panels = [panel for panel in panels if panel.Name.startswith(prefix)]
        logging.info(f"Collected {len(filtered_panels)} panels with prefix '{prefix}'.")
        return filtered_panels
    except Exception as e:
        logging.error(f"Error collecting electrical panels: {e}")
        raise

def get_panel_level(panel):
    """
    Retrieves the level associated with the panel.
    """
    try:
        level_id = panel.LevelId
        level = panel.Document.GetElement(level_id)
        return level
    except Exception as e:
        logging.error(f"Error retrieving level for panel {panel.Id}: {e}")
        return None

def group_panels_by_level(panels):
    """
    Groups panels based on their levels.
    """
    level_panel_map = {}
    for panel in panels:
        level = get_panel_level(panel)
        if level:
            if level.Id not in level_panel_map:
                level_panel_map[level.Id] = {'level': level, 'panels': []}
            level_panel_map[level.Id]['panels'].append(panel)
    return level_panel_map

def get_panel_connections(panel):
    """
    Retrieves connected elements (circuits) for a given electrical panel.
    """
    connections = []
    try:
        electrical_systems = getattr(panel.MEPModel, 'ElectricalSystems', None)
        if electrical_systems:
            for system in electrical_systems:
                connections.extend([elem for elem in system.Elements if elem.Id != panel.Id])
        return connections
    except Exception as e:
        logging.error(f"Error retrieving connections for panel {panel.Id}: {e}")
        return connections

def create_drafting_view(doc, view_name):
    """
    Creates a new drafting view for the one-line diagram or retrieves it if it exists.
    """
    try:
        existing_view = next((v for v in FilteredElementCollector(doc)
                              .OfClass(ViewDrafting)
                              .ToElements()
                              if v.Name == view_name), None)
        if existing_view:
            logging.info(f"Using existing drafting view '{view_name}'.")
            return existing_view

        # Get a ViewFamilyType for drafting views
        view_family_type = next((vft for vft in FilteredElementCollector(doc)
                                 .OfClass(ViewFamilyType)
                                 .ToElements()
                                 if vft.ViewFamily == ViewFamily.Drafting), None)
        if not view_family_type:
            raise Exception("No ViewFamilyType found for Drafting views.")

        with Transaction(doc, 'Create Drafting View') as t:
            t.Start()
            drafting_view = ViewDrafting.Create(doc, view_family_type.Id)
            drafting_view.Name = view_name
            t.Commit()

        logging.info(f"Created new drafting view '{view_name}'.")
        return drafting_view
    except Exception as e:
        logging.error(f"Error creating drafting view: {e}")
        raise

def pick_panel_symbol(doc):
    """
    Lets the user pick a detail item family to use for panel symbols.
    """
    try:
        # Collect all detail item families
        detail_items = list(FilteredElementCollector(doc)
                            .OfCategory(BuiltInCategory.OST_DetailComponents)
                            .WhereElementIsElementType()
                            .ToElements())
        if not detail_items:
            forms.alert(
                msg="No Detail Components found in the project.",
                title="No Symbols Available",
                warn_icon=True
            )
            logging.warning("No Detail Components available.")
            return None

        # Create a dictionary of family symbols
        detail_items_dict = {}
        for item in detail_items:
            key = f"{item.Family.Name} - {item.Name}"
            detail_items_dict[key] = item

        # Prompt the user to select a family type
        selected_item_name = forms.SelectFromList.show(
            sorted(detail_items_dict.keys()),
            title="Select Panel Symbol",
            button_name="Select",
            multiselect=False
        )

        if not selected_item_name:
            logging.info("User canceled symbol selection.")
            return None

        selected_symbol = detail_items_dict.get(selected_item_name)
        logging.info(f"Selected panel symbol: {selected_item_name}")
        return selected_symbol
    except Exception as e:
        logging.error(f"Error selecting panel symbol: {e}")
        raise

def get_user_input():
    """
    Prompts the user for configuration options.
    """
    try:
        components = [
            forms.Label('Enter Panel Name Prefix:'),
            forms.TextBox('prefix', Text=DEFAULT_PANEL_PREFIX),

            forms.Label('Enter Drafting View Name:'),
            forms.TextBox('view_name', Text=DEFAULT_VIEW_NAME),

            forms.Label('Enter Horizontal Spacing:'),
            forms.TextBox('spacing_x', Text=str(DEFAULT_SPACING_X)),

            forms.Label('Enter Vertical Spacing:'),
            forms.TextBox('spacing_y', Text=str(DEFAULT_SPACING_Y)),
        ]

        # Display the form
        response = forms.Dialog.show(components, title='One-Line Diagram Configuration')

        if response:
            prefix = response['prefix']
            view_name = response['view_name']
            spacing_x = float(response['spacing_x'])
            spacing_y = float(response['spacing_y'])
            logging.info("User provided custom configuration.")
            return prefix, view_name, spacing_x, spacing_y
        else:
            logging.info("User canceled configuration.")
            return None
    except Exception as e:
        logging.error(f"Error getting user input: {e}")
        raise

def arrange_layout_by_level(level_panel_map, spacing_x, spacing_y):
    """
    Arranges panel positions grouped by levels.
    """
    layout = {}
    current_x = 0
    current_y = 0

    for level_info in sorted(level_panel_map.values(), key=lambda x: x['level'].Elevation):
        level = level_info['level']
        panels = level_info['panels']

        # Place level label
        layout[level.Id] = {'position': XYZ(current_x, current_y, 0), 'type': 'level', 'name': level.Name}
        current_y -= spacing_y * 2  # Move down for panels

        for panel in panels:
            layout[panel.Id] = {'position': XYZ(current_x, current_y, 0), 'type': 'panel', 'panel': panel}
            current_x += spacing_x

        # Reset x-position and move down for the next level
        current_x = 0
        current_y -= spacing_y * 3  # Additional spacing between levels

    logging.info("Layout arranged based on levels.")
    return layout

def generate_one_line_diagram(doc, view, layout, symbol, sketch_plane):
    """
    Generates the one-line diagram by placing panel symbols and drawing connections.
    """
    try:
        # Activate symbol before the transaction
        if not symbol.IsActive:
            with Transaction(doc, 'Activate Panel Symbol') as t:
                t.Start()
                symbol.Activate()
                t.Commit()

        with Transaction(doc, 'Generate One-Line Diagram') as t:
            t.Start()
            panel_instances = {}
            # Place elements
            for item_id, item_info in layout.items():
                position = item_info['position']
                if item_info['type'] == 'level':
                    # Place level label
                    text_note_type = FilteredElementCollector(doc).OfClass(TextNoteType).FirstElement()
                    text_note = TextNote.Create(
                        doc,
                        view.Id,
                        position,
                        item_info['name'],
                        text_note_type.Id
                    )
                elif item_info['type'] == 'panel':
                    panel = item_info['panel']
                    instance = doc.Create.NewFamilyInstance(position, symbol, view)
                    panel_instances[panel.Id] = instance

            # Draw connection lines
            for item_info in layout.values():
                if item_info['type'] == 'panel':
                    panel = item_info['panel']
                    start_pos = item_info['position']
                    connected_panels = get_panel_connections(panel)
                    for conn_panel in connected_panels:
                        conn_info = layout.get(conn_panel.Id)
                        if conn_info and conn_info['type'] == 'panel':
                            end_pos = conn_info['position']
                            line = Line.CreateBound(start_pos, end_pos)
                            detail_curve = doc.Create.NewDetailCurve(view, line)
                            detail_curve.SketchPlane = sketch_plane
            t.Commit()

        logging.info("One-line diagram generated successfully.")
    except Exception as e:
        logging.error(f"Error generating one-line diagram: {e}")
        raise

def main():
    """
    Main function to execute the one-line diagram creation process.
    """
    doc = revit.doc

    try:
        # Step 1: Get user input
        user_input = get_user_input()
        if not user_input:
            return  # User canceled
        prefix, view_name, spacing_x, spacing_y = user_input

        # Step 2: Collect Electrical Panels
        panels = get_electrical_panels(doc, prefix)
        if not panels:
            forms.alert(
                msg=f"No electrical panels with the prefix '{prefix}' were found.",
                title="No Panels Found",
                warn_icon=True
            )
            logging.warning("No panels found with the specified prefix.")
            return

        # Step 3: Let the user pick detail item symbol
        symbol = pick_panel_symbol(doc)
        if not symbol:
            logging.warning("No symbol selected by the user.")
            return

        # Step 4: Create or retrieve Drafting View
        drafting_view = create_drafting_view(doc, view_name)

        # Step 5: Group Panels by Level
        level_panel_map = group_panels_by_level(panels)
        if not level_panel_map:
            forms.alert(
                msg="No levels found for the panels.",
                title="No Levels Found",
                warn_icon=True
            )
            logging.warning("No levels associated with panels.")
            return

        # Step 6: Arrange Layout
        layout = arrange_layout_by_level(level_panel_map, spacing_x, spacing_y)

        # Step 7: Create a single SketchPlane for all connections
        with Transaction(doc, 'Create SketchPlane') as t:
            t.Start()
            plane = Plane.CreateByNormalAndOrigin(XYZ.BasisZ, XYZ(0, 0, 0))
            sketch_plane = SketchPlane.Create(doc, plane)
            t.Commit()

        # Step 8: Generate One-Line Diagram
        generate_one_line_diagram(doc, drafting_view, layout, symbol, sketch_plane)

        # Step 9: Notify the user of success
        TaskDialog.Show("One-Line Diagram", f"One-line diagram '{view_name}' has been created successfully.")
        logging.info("Script completed successfully.")

    except Exception as e:
        # Handle any unexpected errors
        forms.alert(
            msg=f"An error occurred:\n{str(e)}",
            title="Error",
            warn_icon=True
        )
        logging.error(f"An unexpected error occurred: {e}")

# Execute the script
if __name__ == "__main__":
    main()
