from __future__ import print_function
from Autodesk.Revit.DB import ExternalDefinitionCreationOptions

from pyrevit import revit, forms, script
from Autodesk.Revit.DB import Family, FamilyManager, FamilyParameter, ParameterType, BuiltInParameterGroup, \
    FilteredElementCollector, IFamilyLoadOptions
import os
from System import Enum  # Required to work with .NET enumerations in IronPython

# Initialize document and application
uidoc = __revit__.ActiveUIDocument
doc = uidoc.Document
app = __revit__.Application  # Access the Revit application instance


class FamilyLoadOptions(IFamilyLoadOptions):
    def OnFamilyFound(self, familyInUse, overwriteParameterValues):
        overwriteParameterValues = True
        return True

    def OnSharedFamilyFound(self, sharedFamily, familyInUse, overwriteParameterValues):
        overwriteParameterValues = True
        return True


def get_shared_parameters(doc):
    """Retrieve shared parameters available in the document's shared parameter file."""
    definition_file = app.OpenSharedParameterFile()
    # If no shared parameter file is loaded, prompt the user to pick one
    if not definition_file:
        file_path = forms.pick_file(file_ext='txt', title="Select Shared Parameter File")
        if file_path:
            app.SharedParametersFilename = file_path
            definition_file = app.OpenSharedParameterFile()
        else:
            script.exit("No shared parameter file selected.")

    shared_params = []
    if definition_file:
        for group in definition_file.Groups:
            for definition in group.Definitions:
                shared_params.append(definition)
    return shared_params


def select_shared_parameter(shared_params):
    """Prompt the user to select a shared parameter."""
    param_options = [param.Name for param in shared_params]
    selected_param = forms.SelectFromList.show(param_options, title="Select Shared Parameter", button_name="Select")
    if selected_param:
        return next(param for param in shared_params if param.Name == selected_param)
    return None


def add_shared_parameter_to_families(shared_param, families, param_group):
    """Add the selected shared parameter to each family in the specified parameter group."""
    for family in families:
        # Open family as an editable document
        family_doc = doc.EditFamily(family)
        family_manager = family_doc.FamilyManager

        # Check if the parameter already exists in the family
        existing_param = family_manager.get_Parameter(shared_param.Name)

        if not existing_param:
            try:
                # Start a transaction within the family document
                with revit.Transaction("Add Shared Parameter to Family", family_doc):
                    # Retrieve the ExternalDefinition from the shared parameter file
                    definition_file = app.OpenSharedParameterFile()
                    if definition_file:
                        for group in definition_file.Groups:
                            definition = group.Definitions.get_Item(shared_param.Name)
                            if definition:
                                # Add the parameter directly using FamilyManager in the specified group
                                family_manager.AddParameter(
                                    definition, param_group, False  # False sets it as an instance parameter
                                )
                                print("Parameter", shared_param.Name, "added to family", family.Name, "in group",
                                      param_group)
                                break
                        else:
                            print("Error: Shared parameter definition not found in shared parameter file.")
                            continue
                    else:
                        print("Error: No shared parameter file loaded.")
                        continue
            except Exception as e:
                print("Failed to add parameter", shared_param.Name, "to family", family.Name, ":", e)

        # Save and close the family document
        family_doc.Save()
        family_path = family_doc.PathName
        family_doc.Close(False)

        # Reload the family back into the project
        loaded = doc.LoadFamily(family_path, FamilyLoadOptions())
        if loaded:
            print("Family", family.Name, "successfully reloaded into the project.")
        else:
            print("Warning: Could not reload family", family.Name, "into the project.")


# Step 1: Get and select a shared parameter
shared_params = get_shared_parameters(doc)
if not shared_params:
    script.exit("No shared parameters found in the shared parameters file.")

selected_shared_param = select_shared_parameter(shared_params)
if not selected_shared_param:
    script.exit("No shared parameter was selected.")

# Step 2: Select families (either from a folder or open document)
select_from_folder = forms.alert("Select families from a folder?", options=["Yes", "No"])

family_files = []

# Check for both integer and string values to cover all possible return types
if select_from_folder == 0 or select_from_folder == "Yes":  # User selected "Yes"
    selected_files = forms.pick_file(file_ext="rfa", multi_file=True, title="Select Family Files")
    if selected_files:
        family_files.extend(selected_files)
    else:
        script.exit("No family files were selected.")
elif select_from_folder == 1 or select_from_folder == "No":  # User selected "No"
    # Step 3: Prompt the user to select families from the current document
    all_families = FilteredElementCollector(doc).OfClass(Family).ToElements()
    family_names = [fam.Name for fam in all_families]

    # Display a form to select families
    selected_family_names = forms.SelectFromList.show(family_names, title="Select Families from Document",
                                                      button_name="Select", multiselect=True)
    if not selected_family_names:
        script.exit("No families were selected from the document.")

    # Filter selected families by their names
    family_files = [fam for fam in all_families if fam.Name in selected_family_names]

elif select_from_folder is None:  # User canceled the dialog
    script.exit("Operation canceled by the user.")
else:
    print("Unexpected selection for file source:", select_from_folder)
    script.exit()

# Step 4: Define a dictionary with friendly names for relevant family parameter groups
friendly_param_groups = {
    BuiltInParameterGroup.PG_CONSTRAINTS: "Constraints",
    BuiltInParameterGroup.PG_DATA: "Data",
    BuiltInParameterGroup.PG_GEOMETRY: "Geometry",
    BuiltInParameterGroup.PG_IDENTITY_DATA: "Identity Data",
    BuiltInParameterGroup.PG_MATERIALS: "Materials",
    BuiltInParameterGroup.PG_TEXT: "Text",
    BuiltInParameterGroup.PG_VISIBILITY: "Visibility",
    BuiltInParameterGroup.PG_ANALYSIS_RESULTS: "Analysis Results",
    BuiltInParameterGroup.PG_ELECTRICAL: "Electrical",
    BuiltInParameterGroup.PG_ELECTRICAL_CIRCUITING: "Electrical - Circuiting",
    BuiltInParameterGroup.PG_ELECTRICAL_LIGHTING: "Electrical - Lighting",
    BuiltInParameterGroup.PG_FIRE_PROTECTION: "Fire Protection",
    BuiltInParameterGroup.PG_MECHANICAL: "Mechanical",
    BuiltInParameterGroup.PG_PLUMBING: "Plumbing"
}

# Show the friendly names to the user for selection
friendly_names = list(friendly_param_groups.values())
selected_group_name = forms.SelectFromList.show(friendly_names, title="Select Parameter Group", button_name="Select")

# Map the selected friendly name back to the BuiltInParameterGroup
if selected_group_name:
    param_group = next((key for key, value in friendly_param_groups.items() if value == selected_group_name), None)
    if param_group:
        # Step 5: Add the shared parameter to each selected family in the specified group
        add_shared_parameter_to_families(selected_shared_param, family_files, param_group)
    else:
        script.exit("Selected group name could not be mapped to a BuiltInParameterGroup.")
else:
    script.exit("No parameter group was selected.")

# Notify the user of completion
script.get_logger().info("Shared parameter added to selected families.")
