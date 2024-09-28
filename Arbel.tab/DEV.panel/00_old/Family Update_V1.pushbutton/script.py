from pyrevit import forms, revit
from Autodesk.Revit.DB import Transaction, Family, IFamilyLoadOptions
import clr  # Needed to use StrongBox

# Initialization
uidoc = __revit__.ActiveUIDocument
doc = uidoc.Document


# Custom FamilyLoadOptions class
class CustomFamilyLoadOptions(IFamilyLoadOptions):
    def OnFamilyFound(self, familyInUse, overwriteParameterValues):
        # Overwrite the existing family
        return True

    def OnSharedFamilyFound(self, sharedFamily, overwriteParameterValues):
        # Overwrite shared family
        return True


# Ask the user to select a family file
family_path = forms.pick_file(file_ext='rfa', title='Select Family File to Overwrite')

if family_path:
    with revit.Transaction("Overwrite Family in Project"):
        # Create a StrongBox to hold the family object
        family_box = clr.StrongBox[Family]()

        # Load the selected family file into the project
        load_result = doc.LoadFamily(family_path, CustomFamilyLoadOptions(), family_box)

        if load_result:
            print("Successfully loaded family: {0}".format(family_path))
        else:
            print("Failed to load family: {0}".format(family_path))
