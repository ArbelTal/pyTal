# Import Libraries
from pyrevit import revit, script, forms
from Autodesk.Revit.DB import ElementId, View
import csv
import os
import codecs

# Get the active Revit document
doc = revit.doc

# Prompt the user to select the CSV file
csv_file_path = forms.pick_file(file_ext='csv', title='Select CSV file with View IDs and Names')

# Initialize lists to keep track of opened views and missing views
missing_views = []

if csv_file_path:
    try:
        # Open the CSV file with the appropriate encoding for Python 2.7
        with codecs.open(csv_file_path, mode='r', encoding='utf-8-sig') as csvfile:
            reader = csv.DictReader(csvfile)

            # Strip any whitespace from header names
            headers = [header.strip() for header in reader.fieldnames]

            # Ensure the CSV has the required headers
            if "View ID" not in headers or "View Name" not in headers:
                raise ValueError("CSV file must contain 'View ID' and 'View Name' columns.")

            for row in reader:
                try:
                    view_id_str = row["View ID"].strip()
                    view_name = row["View Name"].strip()

                    # Convert the View ID from string to ElementId
                    if view_id_str.isdigit():
                        view_id = ElementId(int(view_id_str))
                    else:
                        raise ValueError("Invalid View ID: {}".format(view_id_str))

                    # Get the view element from the document
                    view = doc.GetElement(view_id)

                    # Check if the view exists and is not deleted
                    if view is not None and isinstance(view, View):
                        # Open the view in Revit
                        revit.uidoc.RequestViewChange(view)
                    else:
                        # If the view is not found, add to missing views list
                        missing_views.append(view_name)

                except Exception as e:
                    # Handle any other errors that may occur for individual rows
                    missing_views.append(view_name)
                    script.get_output().print_md(
                        "An error occurred while processing view **{}**: {}".format(view_name, e))

        # Print the names of any missing or deleted views
        if missing_views:
            script.get_output().print_md("The following views were not found (may have been deleted):")
            for name in missing_views:
                script.get_output().print_md("- {}".format(name))
        else:
            script.get_output().print_md("All views were successfully opened.")

    except ValueError as ve:
        script.get_output().print_md("An error occurred: {}".format(ve))

    except Exception as e:
        script.get_output().print_md("An unexpected error occurred: {}".format(e))
else:
    script.get_output().print_md("No CSV file selected. Process aborted.")