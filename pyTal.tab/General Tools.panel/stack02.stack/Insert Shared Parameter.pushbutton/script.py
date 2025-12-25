"""Insert Shared Parameter"""
# -*- coding: utf-8 -*-
__title__   = "Insert\nShared Parameter"
__doc__     = """Version = 1.0
Date    = 10.11.2024
________________________________________________________________
Description:
Insert Shared Parameter to families in folder. 
________________________________________________________________
How-To:
1. Choose shared parameter.
2. Select folder containing families.
3. select families to update.
4. Select parameter group.
5. Choose between 'type' and 'instance' for the parameter.
________________________________________________________________
TODO:
________________________________________________________________
Last Updates:
- [01.10.2024] v1.0 Change Description
________________________________________________________________
Author: Arbel Tal"""

from pyrevit import revit, forms, script
from Autodesk.Revit.DB import FilteredElementCollector, BuiltInParameterGroup, SharedParameterElement, FamilyManager, \
    Transaction, IFamilyLoadOptions
"""
from Autodesk.Revit.ApplicationServices import Application
from System.Collections.Generic import List
import clr
"""
import os


# Custom FamilyLoadOptions to always overwrite the family
class FamilyLoadOptions(IFamilyLoadOptions):
    def OnFamilyFound(self, familyInUse, overwriteParameterValues):
        overwriteParameterValues[0] = True  # Overwrite existing families
        return True

    def OnSharedFamilyFound(self, sharedFamily, familyInUse, source, overwriteParameterValues):
        overwriteParameterValues[0] = True  # Overwrite shared families
        return True


# Initialization
uidoc = __revit__.ActiveUIDocument
doc = uidoc.Document
app = doc.Application

# Check if a shared parameter file is loaded, and prompt the user to load one if not
if not app.SharedParametersFilename:
    forms.alert("No shared parameter file is loaded. Please load a shared parameter file and run the script again.",
                exitscript=True)

# Load the shared parameter file
shared_param_file = app.OpenSharedParameterFile()


# Function to collect all shared parameters in the document
def get_shared_parameters():
    shared_params = []
    collector = FilteredElementCollector(doc).OfClass(SharedParameterElement)
    for param in collector:
        shared_params.append(param.GetDefinition().Name)
    return shared_params


# Function to get a dictionary of human-readable parameter group names
def get_parameter_groups():
    param_groups = {
        BuiltInParameterGroup.PG_IDENTITY_DATA: "Identity Data",
        BuiltInParameterGroup.PG_GEOMETRY: "Geometry",
        BuiltInParameterGroup.PG_CONSTRAINTS: "Constraints",
        BuiltInParameterGroup.PG_TEXT: "Text",
        BuiltInParameterGroup.PG_GRAPHICS: "Graphics",
        BuiltInParameterGroup.PG_DATA: "Data",
        BuiltInParameterGroup.PG_IFC: "IFC",
        BuiltInParameterGroup.PG_MATERIALS: "Materials and Finishes",
        BuiltInParameterGroup.PG_GENERAL: "General"
    }
    return param_groups


# Prompt user to select a shared parameter
shared_parameters = get_shared_parameters()
selected_param_name = forms.SelectFromList.show(
    shared_parameters, title="Select a Shared Parameter", multiselect=False
)

if selected_param_name:
    # Find the corresponding ExternalDefinition in the shared parameter file
    selected_definition = None
    for group in shared_param_file.Groups:
        for external_def in group.Definitions:
            if external_def.Name == selected_param_name:
                selected_definition = external_def
                break
        if selected_definition:
            break

    if not selected_definition:
        forms.alert("Shared parameter '{}' not found in the shared parameter file.".format(selected_param_name),
                    exitscript=True)

    # Prompt user to select folder containing family files
    family_folder = forms.pick_folder(title="Select Folder Containing Families")
    if not family_folder:
        forms.alert("No folder selected. Script will exit.", exitscript=True)

    # Get all family files (.rfa) in the selected folder
    all_family_files = [f for f in os.listdir(family_folder) if f.endswith(".rfa")]

    # Ask user to select specific families from the folder
    selected_family_files = forms.SelectFromList.show(
        all_family_files, title="Select Families to Update", multiselect=True
    )

    if selected_family_files:
        # Get parameter group names in a readable format
        param_groups = get_parameter_groups()
        selected_group_name = forms.SelectFromList.show(
            list(param_groups.values()), title="Select Parameter Group", multiselect=False
        )

        # Ask the user to choose between 'type' and 'instance' for the parameter
        is_instance = forms.alert(
            "Do you want the parameter to be 'instance' or 'type'?",
            options=["Instance", "Type"]
        ) == "Instance"

        if selected_group_name:
            # Find the corresponding BuiltInParameterGroup for the selected name
            selected_group = next(
                (key for key, value in param_groups.items() if value == selected_group_name), None
            )

            # Iterate through selected family files and add shared parameter if not present
            for family_file in selected_family_files:
                family_path = os.path.join(family_folder, family_file)

                try:
                    # Open the family file
                    family_doc = app.OpenDocumentFile(family_path)
                    family_manager = family_doc.FamilyManager

                    # Check if the parameter already exists
                    param_exists = any(
                        param.Definition.Name == selected_param_name for param in family_manager.Parameters)

                    if not param_exists:
                        # Start transaction within the family document to add the parameter
                        with Transaction(family_doc, 'Add Shared Parameter to Family') as t:
                            t.Start()
                            family_manager.AddParameter(
                                selected_definition, selected_group, is_instance
                                # Set True for instance-based, False for type-based
                            )
                            t.Commit()
                        print("Added parameter '{}' to family '{}'.".format(selected_param_name, family_file))
                    else:
                        print("Parameter '{}' already exists in family '{}'. Skipping.".format(selected_param_name,
                                                                                               family_file))

                    # Save and close the family document
                    family_doc.Save()
                    family_doc.Close(False)

                except InvalidOperationException as e:
                    print("Error processing family '{}': {}".format(family_file, e))

            print("Processing complete for selected families.")
