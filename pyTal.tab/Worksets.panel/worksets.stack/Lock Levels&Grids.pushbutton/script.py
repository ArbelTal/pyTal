from pyrevit import revit, DB, script

doc = revit.doc

TARGET_WORKSET_NAME = "Shared Levels and Grids"

def get_or_create_workset(doc, name):
    # type: (DB.Document, str) -> DB.WorksetId
    if not doc.IsWorkshared:
        return None
    
    # Check if workset exists
    filtered_worksets = DB.FilteredWorksetCollector(doc).OfKind(DB.WorksetKind.UserWorkset)
    for ws in filtered_worksets:
        if ws.Name == name:
            return ws.Id
            
    # Create if not found
    return DB.Workset.Create(doc, name).Id

def process_elements():
    logger = script.get_output()
    
    # Collect Grids and Levels
    # We use a multi-category filter or just union two collectors
    cats = [DB.BuiltInCategory.OST_Grids, DB.BuiltInCategory.OST_Levels]
    # In older APIs checks might differ, but IsWorkshared check handles the environment.
    
    # Start Transaction
    t = DB.Transaction(doc, "Move and Pin Levels/Grids")
    t.Start()
    
    try:
        target_ws_id = get_or_create_workset(doc, TARGET_WORKSET_NAME)
        
        collector = DB.FilteredElementCollector(doc).WhereElementIsNotElementType()
        filter_cats = DB.ElementMulticategoryFilter(System.Collections.Generic.List[DB.BuiltInCategory](cats))
        elements = collector.WherePasses(filter_cats).ToElements()
        
        count_moved = 0
        count_pinned = 0
        
        for el in elements:
            # Move Workset
            if target_ws_id:
                param = el.get_Parameter(DB.BuiltInParameter.ELEM_PARTITION_PARAM)
                if param and param.IsReadOnly == False:
                     # Check if already on workset to avoid unnecessary edit? 
                     # Actually setting it ensures it's correct.
                     current_id = param.AsInteger()
                     if current_id != target_ws_id.IntegerValue:
                         param.Set(target_ws_id.IntegerValue)
                         count_moved += 1
            
            # Pin
            if not el.Pinned:
                el.Pinned = True
                count_pinned += 1
                
        t.Commit()
        
        logger.print_md("## Result")
        logger.print_md("**Processed {} elements**".format(len(elements)))
        if doc.IsWorkshared:
            logger.print_md("- Moved to '{}': **{}**".format(TARGET_WORKSET_NAME, count_moved))
        else:
            logger.print_md("- Model is not workshared, skipped workset reassignment.")
        logger.print_md("- Pinned: **{}**".format(count_pinned))
        
    except Exception as e:
        t.RollBack()
        logger.print_md("## Error")
        logger.print_md(str(e))

import System

if __name__ == '__main__':
    process_elements()
