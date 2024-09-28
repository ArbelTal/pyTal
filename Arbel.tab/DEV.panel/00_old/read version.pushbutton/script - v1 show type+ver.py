from pyrevit import forms, revit
from Autodesk.Revit.DB import StorageType, OpenOptions
from Autodesk.Revit.DB import ModelPathUtils
import os

# Initialize Revit document
uidoc = __revit__.ActiveUIDocument
app = __revit__.Application

# Prompt user to select a family file from a folder
family_path = forms.pick_file(file_ext='rfa', multi_file=False)

if family_path and os.path.exists(family_path):
    # Create a Revit document object from the selected family file without loading into project
    model_path = ModelPathUtils.ConvertUserVisiblePathToModelPath(family_path)
    open_opts = OpenOptions()  # Options for opening a family file
    family_doc = app.OpenDocumentFile(model_path, open_opts)

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
                        print("Family Type: {0}, Version: {1}".format(fam_type.Name, version_value))
                        break
                else:
                    print("Family Type: {0}, 'Version' parameter not found or not an integer.".format(fam_type.Name))

    # Close the family document
    family_doc.Close(False)
else:
    print("No valid family file selected.")
