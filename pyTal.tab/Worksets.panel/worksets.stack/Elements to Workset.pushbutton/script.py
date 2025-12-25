# -*- coding: utf-8 -*-
import csv
import os
import sys
import codecs

from pyrevit import revit, DB, script, forms

# Get the directory of the current script
script_dir = os.path.dirname(__file__)

doc = revit.doc
output = script.get_output()

def get_workset_map(doc):
    """Returns a dictionary {WorksetName: WorksetId}."""
    worksets = DB.FilteredWorksetCollector(doc).OfKind(DB.WorksetKind.UserWorkset)
    return {w.Name: w.Id for w in worksets}

def get_category_map(doc):
    """Returns a dictionary {CategoryName: CategoryId}."""
    # Using doc.Settings.Categories to get all categories
    return {c.Name: c.Id for c in doc.Settings.Categories}

def read_csv_data(filepath):
    """Reads CSV with UTF-8 handling and returns list of dicts."""
    data = []
    if not os.path.exists(filepath):
        return data
        
    try:
        # Use codecs to safely read utf-8, handling BOM if present
        with codecs.open(filepath, 'r', 'utf-8-sig') as f:
            lines = f.readlines()
            
        if not lines:
            return data
            
        # Parse header
        header = [h.strip() for h in lines[0].split(',')]
        
        for line in lines[1:]:
            parts = [p.strip() for p in line.split(',')]
            if len(parts) >= 2:
                # Basic mapping based on position or finding index if header matches
                # Assuming order: category, workset
                row = {}
                row['category'] = parts[0].title()
                row['workset'] = parts[1]
                data.append(row)
    except Exception as e:
        output.print_md("## Error reading CSV: {}".format(e))
        
    return data

def main():
    # 1. Pick CSV File
    csv_path = forms.pick_file(file_ext='csv')
    if not csv_path:
        # User canceled
        return

    # Check if worksharing is enabled
    if not doc.IsWorkshared:
        output.print_md("## Error: Model is not workshared.")
        return

    # 2. Read CSV Data
    csv_rows = read_csv_data(csv_path)
    if not csv_rows:
        output.print_md("## No valid data found in `worksets.csv`.")
        return

    # 2. Verify / Create Worksets
    required_worksets = set(row['workset'] for row in csv_rows if row['workset'])
    workset_map = get_workset_map(doc)
    
    t_create = DB.Transaction(doc, "Create Missing Worksets")
    t_create.Start()
    
    created_count = 0
    for ws_name in required_worksets:
        if ws_name not in workset_map:
            try:
                # Create the workset
                new_ws = DB.Workset.Create(doc, ws_name)
                workset_map[ws_name] = new_ws.Id
                created_count += 1
            except Exception as e:
                print("Failed to create Workset '{}': {}".format(ws_name, e))
    
    t_create.Commit()
    
    # 3. Collect Elements to Move
    category_map = get_category_map(doc)
    
    elements_to_move = [] # List of tuples (Element, WorksetId, CategoryName, WorksetName)
    
    for row in csv_rows:
        cat_name = row['category']
        ws_name = row['workset']
        
        cat_id = category_map.get(cat_name)
        ws_id = workset_map.get(ws_name)
        
        if not cat_id:
            print("Warning: Category '{}' not found in project.".format(cat_name))
            continue
        if not ws_id:
            print("Warning: Workset '{}' not found (creation failed?).".format(ws_name))
            continue
            
        # Collect elements for this category
        collector = DB.FilteredElementCollector(doc).OfCategoryId(cat_id).WhereElementIsNotElementType()
        for elem in collector.ToElements():
            elements_to_move.append((elem, ws_id, cat_name, ws_name))

    if not elements_to_move:
        output.print_md("## No elements found to move.")
        return

    # 4. Move Elements with Progress Bar
    t_move = DB.Transaction(doc, "Move Elements to Worksets")
    t_move.Start()
    
    total_elements = len(elements_to_move)
    moved_count = 0
    
    # Create Progress Bar
    # cancellable=True adds a Cancel button
    with forms.ProgressBar(title='Moving Elements... ({value}/{max_value})', cancellable=True) as pb:
        for i, (elem, ws_id, cat_name, ws_name) in enumerate(elements_to_move):
            if pb.cancelled:
                output.print_md("## Operation Cancelled by User. Rolling back...")
                t_move.RollBack()
                return

            # Update Progress
            pb.update_progress(i, total_elements)
            
            # Logic to move element
            param = elem.get_Parameter(DB.BuiltInParameter.ELEM_PARTITION_PARAM)
            if param and not param.IsReadOnly:
                current_val = param.AsInteger()
                new_val = ws_id.IntegerValue
                
                if current_val != new_val:
                    param.Set(new_val)
                    moved_count += 1
    
    t_move.Commit()

if __name__ == "__main__":
    main()
