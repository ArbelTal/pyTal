from pyrevit import revit, DB, UI
from pyrevit import forms

# Initialize document
uidoc = __revit__.ActiveUIDocument
doc = uidoc.Document

# Collect all families in the document
collector = DB.FilteredElementCollector(doc).OfClass(DB.Family)

# Filter families with prefix "SN_"
SN_families = [fam for fam in collector if fam.Name.startswith("SN_")]

# Prepare the list of family names for the UI
SN_family_names = [fam.Name for fam in SN_families]

# Show a multi-selection UI to the user
selected_families = forms.SelectFromList.show(
    SN_family_names,
    title="Select SN_Families",
    multiselect=True
)

# If families were selected, print their names
if selected_families:
    for family_name in selected_families:
        print("Selected Family: {0}".format(family_name))