#import Libraries
from pyrevit import revit, script, forms, DB

#Get uidoc and open views
doc = revit.doc
uidoc = revit.uidoc

# Get Views to reOpen
try:
    id_string = script.load_data("ViewMemory", this_project = True)
except:
    id_string = ""

#catch if no data to use
if id_string == "":
    forms.alert("Data could not be found.", title = "Script cancelled")
    script.exit()

# Try to open the views
failures = 0

for i in id_string.split(","):
    try:
        view_id = DB.ElementId(int(i))
        uidoc.ActiveView = doc.GetElement(view_id)
    except:
        failures += 1

if failures != 0:
    forms.alert("Some view could not be found.", title = "Script completed")