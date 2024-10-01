# -*- coding: utf-8 -*-
from pyrevit import revit, DB, UI
from pyrevit import forms

# Initialize document
uidoc = __revit__.ActiveUIDocument
doc = uidoc.Document

# Collect all families in the document
collector = DB.FilteredElementCollector(doc).OfClass(DB.Family)

# Function to retrieve the version parameter value
def get_version_parameter(family):
    version = None
    family_symbol_ids = family.GetFamilySymbolIds()

    # Loop through family types (symbols)
    for symbol_id in family_symbol_ids:
        symbol = doc.GetElement(symbol_id)  # Get the family type
        version_param = symbol.LookupParameter("Version")

        # Check if 'Version' parameter exists and is of integer type
        if version_param and version_param.StorageType == DB.StorageType.Integer:
            version = version_param.AsInteger()
            break  # Assume all types in the family share the same version

    return version

# Filter families with prefix "SN_"
SN_families = [fam for fam in collector if fam.Name.startswith("SN_")]

# Prepare the list of family names and versions for the UI (ensure Unicode)
family_name_with_version = []
for fam in SN_families:
    family_name = unicode(fam.Name)
    version = get_version_parameter(fam)
    version_str = unicode(version) if version is not None else u"N/A"
    display_name = u"{} (Version: {})".format(family_name, version_str)
    family_name_with_version.append(display_name)

# Show a multi-selection UI to the user
selected_families_with_version = forms.SelectFromList.show(
    family_name_with_version,
    title="Select SN_Families",
    multiselect=True
)

# If families were selected, print their names with versions
if selected_families_with_version:
    print("Selected Families:")
    for family_display in selected_families_with_version:
        print(family_display)
