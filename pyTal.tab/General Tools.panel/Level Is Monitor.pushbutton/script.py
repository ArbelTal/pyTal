from pyrevit import revit, DB, script

doc = revit.doc

# Collect all Level elements
levels_collector = DB.FilteredElementCollector(doc)\
                     .OfClass(DB.Level)\
                     .WhereElementIsNotElementType()\
                     .ToElements()

data = []

is_workshared = doc.IsWorkshared

for level in levels_collector:
    # Check if the level is copy/monitored
    monitored_ids = level.GetMonitoredLinkElementIds()
    is_monitored = True if monitored_ids and len(monitored_ids) > 0 else False
    
    # Elevation
    elevation = "{:.2f}".format(level.Elevation)

    # Workset
    workset_name = "-"
    if is_workshared:
        ws = doc.GetWorksetTable().GetWorkset(level.WorksetId)
        if ws:
            workset_name = ws.Name

    # Scope Box
    scope_box_name = "-"
    sb_param = level.LookupParameter("Scope Box")
    if sb_param:
        sb_id = sb_param.AsElementId()
        if sb_id != DB.ElementId.InvalidElementId:
            sb_elem = doc.GetElement(sb_id)
            if sb_elem:
                scope_box_name = sb_elem.Name

    # Conditional styling
    if not is_monitored:
        status_display = '<span style="color:red; font-weight:bold;">False</span>'
        level_name_display = '<span style="color:red; font-weight:bold;">{}</span>'.format(level.Name)
    else:
        status_display = "True"
        level_name_display = level.Name
    
    data.append([level_name_display, status_display, elevation, workset_name, scope_box_name])

# Sort data by Elevation (index 2)
data.sort(key=lambda x: float(x[2]))

# Output the results in a table
output = script.get_output()
output.print_table(table_data=data, columns=["Level Name", "Is Monitored", "Elevation", "Workset", "Scope Box"])
