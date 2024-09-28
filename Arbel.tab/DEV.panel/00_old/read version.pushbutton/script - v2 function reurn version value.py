from pyrevit import forms, revit
from Autodesk.Revit.DB import StorageType, OpenOptions
from Autodesk.Revit.DB import ModelPathUtils
import os

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
                        print("Family Type: {0}, 'Version' parameter not found or not an integer.".format(fam_type.Name))

    except Exception as e:
        print("Error getting family version: {}".format(e))
    finally:
        # Close the family document
        family_doc.Close(False)

    return version_value

# Example usage
family_path = forms.pick_file(file_ext='rfa', multi_file=False)
version = get_family_version(family_path)

if version:
    print("Family Version: {}".format(version))
else:
    print("No valid family file selected or version not found.")