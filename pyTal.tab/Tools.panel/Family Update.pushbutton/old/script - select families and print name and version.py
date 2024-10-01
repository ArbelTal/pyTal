# -*- coding: utf-8 -*-
from pyrevit import revit, DB, UI
from pyrevit import forms

# Initialize document
uidoc = __revit__.ActiveUIDocument
doc = uidoc.Document

# Collect all families in the document
collector = DB.FilteredElementCollector(doc).OfClass(DB.Family)

# Filter families with prefix "SN_"
SN_families = [fam for fam in collector if fam.Name.startswith("SN_")]

# Prepare the list of family names for the UI (ensure Unicode)
SN_family_names = [unicode(fam.Name) for fam in SN_families]

# Show a multi-selection UI to the user
selected_families = forms.SelectFromList.show(
    SN_family_names,
    title="Select SN_Families",
    multiselect=True
)

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


# Test Printing Table Header
print(u"Family Name".ljust(40) + u"Version")

# If families were selected, print the table rows with debugging
if selected_families:
    for family_name in selected_families:
        try:
            # Find the corresponding family object
            family = next(fam for fam in SN_families if unicode(fam.Name) == family_name)

            # Debugging: Print the family name
            print(u"\nProcessing Family: {}".format(family_name))

            # Get the version parameter value
            version = get_version_parameter(family)

            # Debugging: Print the version, even if it's None
            if version is not None:
                print(u"Version: {}".format(version))
            else:
                print(u"Version: N/A")

            """# Simplified Output of Family Name and Version (without column constraints)
            family_name_str = family_name.ljust(40)
            version_str = unicode(version) if version is not None else u"N/A"
            print(family_name_str + version_str)"""

        except Exception as e:
            # Print detailed error message for troubleshooting
            print("Error processing family: {}".format(family_name))
            print(str(e))
