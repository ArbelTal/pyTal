# -*- coding: utf-8 -*-
"""Sort views by project and level."""

import traceback
from pyrevit import revit, DB, UI, forms, script

def get_view_project(view):
    """Attempt to get a 'Project' parameter from a view."""
    proj_param = view.LookupParameter("Project")
    if not proj_param:
        proj_param = view.LookupParameter("פרויקט") # Fallback for Hebrew templates
    
    if proj_param and proj_param.HasValue:
        return proj_param.AsString()
    return "No Project"

def get_view_level_sort_key(view):
    """Attempt to get the level sort key (Elevation, Name) of a view."""
    try:
        gen_level = view.GenLevel
        if gen_level:
            return (gen_level.Elevation, gen_level.Name)
    except Exception:
        pass
        
    return (float('inf'), "No Level")

def main():
    uiapp = __revit__
    app = uiapp.Application
    
    class ViewItem(object):
        def __init__(self, doc, uidoc, uiview, view):
            self.doc = doc
            self.uidoc = uidoc
            self.uiview = uiview
            self.view = view
            self.doc_name = doc.Title
            self.project = get_view_project(view)
            self.level_sort_key = get_view_level_sort_key(view)
            self.name = view.Name

    view_items = []
    
    valid_view_types = [
        DB.ViewType.FloorPlan, DB.ViewType.CeilingPlan, 
        DB.ViewType.EngineeringPlan, DB.ViewType.AreaPlan, 
        DB.ViewType.Section, DB.ViewType.Elevation, 
        DB.ViewType.ThreeD, DB.ViewType.DraftingView
    ]

    # 1. Collect open views for the ACTIVE document
    active_uidoc = uiapp.ActiveUIDocument
    active_doc = active_uidoc.Document
    
    open_uvs = active_uidoc.GetOpenUIViews()
    for uv in open_uvs:
        v = active_doc.GetElement(uv.ViewId)
        if v and not v.IsTemplate and v.ViewType in valid_view_types:
            view_items.append(ViewItem(active_doc, active_uidoc, uv, v))

    if not view_items:
        forms.alert("No open valid views found in the active model.", exitscript=True)

    # Sort views by Project -> Level Elevation -> Name
    view_items.sort(key=lambda x: (x.project, x.level_sort_key, x.name))

    # Reorder tabs in Revit UI by closing and reopening
    try:
        active_view_id = active_uidoc.ActiveView.Id
        
        # We need an "anchor" view to keep the document open while we close all other views.
        # If we just keep one of the open views, it will stay in its original tab position,
        # which splits the group. So we try to find a closed view to use as a temporary anchor.
        open_view_ids = [uv.ViewId for uv in open_uvs]
        all_views = DB.FilteredElementCollector(active_doc).OfClass(DB.View).ToElements()
        
        dummy_view = None
        for v in all_views:
            if v.Id not in open_view_ids and not v.IsTemplate and v.ViewType in valid_view_types:
                dummy_view = v
                break
                
        if dummy_view:
            # Open the dummy view to keep the document alive (it opens at the far right)
            active_uidoc.ActiveView = dummy_view
            
            # Close all originally open views
            for vi in view_items:
                vi.uiview.Close()
                
            # Open them in sorted order (they stack to the right of the dummy view)
            for vi in view_items:
                active_uidoc.ActiveView = vi.view
                
            # Close the dummy view
            current_uvs = active_uidoc.GetOpenUIViews()
            for uv in current_uvs:
                if uv.ViewId == dummy_view.Id:
                    uv.Close()
                    break
        else:
            # Fallback if every single valid view in the project is already open
            kept_view = None
            for vi in view_items:
                if vi.view.Id == active_view_id:
                    kept_view = vi
                    break
            if not kept_view:
                kept_view = view_items[0]
                
            for vi in view_items:
                if vi.view.Id != kept_view.view.Id:
                    vi.uiview.Close()
                    
            for vi in view_items:
                if vi.view.Id != kept_view.view.Id:
                    active_uidoc.ActiveView = vi.view
                    
        # Finally reactivate the original active view
        for vi in view_items:
            if vi.view.Id == active_view_id:
                active_uidoc.ActiveView = vi.view
                break
                
    except Exception as e:
        forms.alert(str(e))

if __name__ == '__main__':
    main()
