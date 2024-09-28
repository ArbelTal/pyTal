# Import Libraries
from pyrevit import revit, script, forms
import csv
import os
import re
import codecs

# Get uidoc and open views
uidoc = revit.uidoc
doc = revit.doc
ui_views = uidoc.GetOpenUIViews()

# Get the Revit model name
model_name = doc.Title  # Get the Revit model name

# Sanitize the model name to remove invalid characters for file names
sanitized_model_name = re.sub(r'[\/:*?"<>|]', "_", model_name)

# Prompt the user to select a folder to save the CSV file
output_folder = forms.pick_folder(title='Select Folder to Save Views CSV')

if output_folder:
    # Define the file path for the CSV with model name appended to "_Views.csv"
    file_name = sanitized_model_name+"_Views.csv"
    file_path = os.path.join(output_folder, file_name)

    # Get view IDs and names
    view_data = []

    for v in ui_views:
        view_id = v.ViewId
        view = doc.GetElement(view_id)

        # Ensure the element is a view and get the name in Unicode
        if view and view.ViewType:
            view_name = view.Name  # Use the raw name directly, expecting Unicode (Hebrew)
            view_data.append((view_id.ToString(), view_name))

    # Convert view data to a string for logging
    try:
        view_data_str = u"\n".join(u"{}, {}".format(view_id, view_name) for view_id, view_name in view_data)
    except Exception as e:
        script.write("Error creating view data string: {}".format(e))

    # Store view data into log file
    script.store_data("ViewDataMemory", view_data_str, this_project=True)

    # Save view data to a CSV file
    try:
        # Use 'utf-8-sig' to ensure correct encoding and avoid issues with Excel's handling of BOM
        with codecs.open(file_path, mode='w', encoding='utf-8-sig') as file:
            writer = csv.writer(file)
            writer.writerow([u"View ID", u"View Name"])  # Header row
            writer.writerows(view_data)  # Write view data rows
        print("View names and IDs have been saved to {}.".format(file_path))
    except Exception as e:
        print("An error occurred while saving the file: {}".format(e))
else:
    print("No folder selected. Process aborted.")
