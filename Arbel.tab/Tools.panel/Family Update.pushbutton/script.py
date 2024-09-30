# -*- coding: utf-8 -*-
from pyrevit import revit, DB, forms
import os
from Autodesk.Revit.DB import OpenOptions, ModelPathUtils, StorageType, Transaction, IFamilyLoadOptions

# Initialize document
uidoc = __revit__.ActiveUIDocument
doc = uidoc.Document
app = __revit__.Application  # Access Revit application object


# Custom FamilyLoadOptions to handle existing families
class FamilyLoadOptions(IFamilyLoadOptions):
    def OnFamilyFound(self, familyInUse, overwriteParameterValues):
        # Always return True to overwrite existing families
        overwriteParameterValues = True
        return True

    def OnSharedFamilyFound(self, sharedFamily, familyInUse, source, overwriteParameterValues):
        # Overwrite shared families
        overwriteParameterValues = True
        return True


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


# New Function to retrieve the version parameter from a family file
def get_family_version(family_path):
    """
    This function takes a family file path and returns the "Version" parameter value as an integer.

    Args:
        family_path (str): Path to the family file.

    Returns:
        int: Version value of the family type (if found), or None if not found or invalid.
    """

    if not family_path or not os.path.exists(family_path):
        return None

    # Initialize Revit document
    uidoc = __revit__.ActiveUIDocument
    app = __revit__.Application

    # Create a Revit document object from the selected family file without loading into project
    model_path = ModelPathUtils.ConvertUserVisiblePathToModelPath(family_path)
    open_opts = OpenOptions()  # Options for opening a family file
    family_doc = app.OpenDocumentFile(model_path, open_opts)

    version_value = None

    try:
        # Open a transaction to interact with the family file
        with revit.Transaction('Read Family Version', doc=family_doc):
            # Check if the document contains family
            family_mgr = family_doc.FamilyManager

            if family_mgr:
                # Loop through family types
                family_types = family_mgr.Types
                for fam_type in family_types:
                    # Set the current type to access its parameters
                    family_mgr.CurrentType = fam_type

                    # Loop through parameters to find "Version"
                    for param in family_mgr.GetParameters():
                        if param.Definition.Name == "Version" and param.StorageType == StorageType.Integer:
                            version_value = family_mgr.CurrentType.AsInteger(param)
                            break  # Exit inner loop once version is found
                    else:
                        print(
                            "Family Type: {0}, 'Version' parameter not found or not an integer.".format(fam_type.Name))

    except Exception as e:
        print("Error getting family version: {0}".format(e))
    finally:
        # Close the family document
        family_doc.Close(False)

    return version_value


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

    # Get the family version from the file
    file_version = get_family_version(family_path)

    # If the family is already in the project
    family_name = os.path.splitext(family_file)[0]
    if family_name in project_families:
        # Get version parameter from the project
        project_family = project_families[family_name]
        project_version = get_version_parameter_from_project(project_family)

        # Format versions as strings for display
        project_version_str = str(project_version) if project_version is not None else "N/A"
        file_version_str = str(file_version) if file_version is not None else "N/A"

        # Add the family comparison data to the list with a clear "[DIFFERENT]" prefix for version differences
        if project_version != file_version:
            display_name = "[DIFFERENT] {} (Project Version: {}, Folder Version: {})".format(
                family_name, project_version_str, file_version_str)
        else:
            display_name = "{} (Project Version: {}, Folder Version: {})".format(
                family_name, project_version_str, file_version_str)

        family_comparison.append((display_name, family_path))  # Store display name and file path for selected families

# Step 5: Show a multi-selection UI to the user with family names and version comparison
selected_families_comparison = forms.SelectFromList.show(
    [display[0] for display in family_comparison],  # Show only display names
    title="Compare Project and Folder Families Versions",
    multiselect=True
)

# Step 6: If families were selected, update them in the project
if selected_families_comparison:
    # Get the selected family paths for updating
    selected_families_paths = [
        family_comparison[i][1] for i, display_name in enumerate([display[0] for display in family_comparison])
        if display_name in selected_families_comparison
    ]

    # Start a transaction to load the selected families into the project
    with Transaction(doc, 'Load Selected Families') as t:
        t.Start()
        for family_path in selected_families_paths:
            try:
                # Use custom FamilyLoadOptions to overwrite existing families
                family_loaded = doc.LoadFamily(family_path, FamilyLoadOptions())

                if family_loaded:
                    print("Successfully updated family from: {0}".format(family_path))
                else:
                    print("Failed to load family from: {0}".format(family_path))
            except Exception as e:
                print("Error loading family: {0}, Error: {1}".format(family_path, e))
        t.Commit()

    forms.alert("Selected families have been updated.")
