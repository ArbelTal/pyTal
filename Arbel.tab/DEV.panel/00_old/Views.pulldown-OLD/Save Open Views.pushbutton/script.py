# import Libraries
from pyrevit import revit, script
#import Libraries
from pyrevit import revit, script

#Get uidoc and open views
uidoc = revit.uidoc
ui_views = uidoc.GetOpenUIViews()


#get views ids
view_ids = []

for v in ui_views:
    id_string = v.ViewId.ToString()
    view_ids.append(id_string)

id_string = ",".join(view_ids)
#print(id_string)


# Store views IDs into log file
script.store_data("ViewMemory", id_string, this_project = True)
# Store views names into log file
#script.store_data("ViewNameMemory", name_string, this_project = True)