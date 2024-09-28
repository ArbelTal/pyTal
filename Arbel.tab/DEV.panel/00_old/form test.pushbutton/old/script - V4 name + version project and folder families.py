# -*- coding: utf-8 -*-
from pyrevit import revit, DB, forms
import os

# Initialize document
uidoc = __revit__.ActiveUIDocument
doc = uidoc.Document
app = __revit__.Application  # Access Revit application object


# Function to retrieve the version parameter value from a family in the project
def get_version_parameter_from_project(family):
    version = None
    family_symbol_ids = family.GetFamilySymbolIds()

    for symbol_id in family_symbol_ids:
        symbol = doc.GetElement(symbol_id)  # Get the family type (symbol)
        version_param = symbol.LookupParameter("Version")

        # Check if 'Version' parameter exists and is of integer type
        if version_param and version_param.StorageType == DB.StorageType.Integer:
            version = version_param.AsInteger()
            break  # Return the first found "Version" value

    return version


# Function to retrieve the version parameter from a family file
def get_version_parameter_from_file(family_doc):
    version = None
    collector = DB.FilteredElementCollector(family_doc).OfClass(DB.Family)

    for fam in collector:
        family_symbol_ids = fam.GetFamilySymbolIds()
        for symbol_id in family_symbol_ids:
            symbol = family_doc.GetElement(symbol_id)  # Get the family type
            version_param = symbol.LookupParameter("Version")

            # Check if 'Version' parameter exists and is of integer type
            if version_param and version_param.StorageType == DB.StorageType.Integer:
                version = version_param.AsInteger()
                return version  # Return the first found "Version" value

    return version


# Step 1: Collect all families currently loaded in the project
collector = DB.FilteredElementCollector(doc).OfClass(DB.Family)
project_families = {fam.Name: fam for fam in collector}

# Step 2: Prompt the user to select a folder containing families
selected_folder = forms.pick_folder(title="Select Folder with Families")
if not selected_folder:
    forms.alert("No folder selected. Exiting.", exitscript=True)

# Step 3: Get all family files in the folder (only .rfa files)
family_files = [f for f in os.listdir(selected_folder) if f.endswith('.rfa')]

# List to store family comparison information
family_comparison = []

# Step 4: Compare project families and families from the folder
for family_file in family_files:
    family_path = os.path.join(selected_folder, family_file)

    # Open the family file in a temporary document
    family_doc = app.OpenDocumentFile(family_path)
    family_name = family_doc.Title

    # If the family is already in the project
    if family_name in project_families:
        # Get version parameter from the project
        project_family = project_families[family_name]
        project_version = get_version_parameter_from_project(project_family)

        # Get version parameter from the family file
        file_version = get_version_parameter_from_file(family_doc)

        # Format versions as strings for display
        project_version_str = str(project_version) if project_version is not None else "N/A"
        file_version_str = str(file_version) if file_version is not None else "N/A"

        # Add the family comparison data to the list
        display_name = "{} (Project Version: {}, Folder Version: {})".format(family_name, project_version_str,
                                                                             file_version_str)
        family_comparison.append(display_name)

    # Close the family file
    family_doc.Close(False)  # False means we are closing without saving any changes

# Step 5: Show a multi-selection UI to the user with family names and version comparison
selected_families_comparison = forms.SelectFromList.show(
    family_comparison,
    title="Compare SN_Families Versions",
    multiselect=True
)

# Step 6: If families were selected, print their comparison
if selected_families_comparison:
    print("Selected Families Comparison:")
    for family_display in selected_families_comparison:
        print(family_display)
