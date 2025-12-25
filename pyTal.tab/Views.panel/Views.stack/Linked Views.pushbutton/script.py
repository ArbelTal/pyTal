import clr
import csv

# Load Revit API and System libraries FIRST
clr.AddReference('RevitAPI')
clr.AddReference('RevitAPIUI')
clr.AddReference('System.Windows.Forms')

import System
import System.Windows.Forms as WinForms
from Autodesk.Revit.DB import *

# Import PyRevit's script utilities
from pyrevit import script

# --- Output Wrapper Class ---
# PyRevitOutputWindow doesn't always support .write(), so we wrap it.
class OutputWrapper:
    def write(self, msg):
        print(msg.rstrip('\n'))

output_stream = OutputWrapper()

# Global Document Access
doc = __revit__.ActiveUIDocument.Document

def select_csv_file():
    """
    Opens a file dialog for the user to select a CSV file.
    Returns the selected file path or None if no file is selected.
    """
    ofd = WinForms.OpenFileDialog()
    ofd.Filter = "CSV files (*.csv)|*.csv|All files (*.*)|*."
    ofd.Title = "Select CSV File"
    if ofd.ShowDialog() == WinForms.DialogResult.OK:
        return ofd.FileName
    return None

def get_view_by_name(doc, name):
    """
    Retrieves a view from the given document by its name.
    Filters out view templates.
    """
    # Define view types that typically support SetLinkedView
    supported_view_types = [
        ViewType.FloorPlan,
        ViewType.CeilingPlan,
        ViewType.Section,
        ViewType.Elevation,
        ViewType.ThreeD
    ]

    for v in FilteredElementCollector(doc).OfClass(View):
        if v.Name == name and not v.IsTemplate:
            if v.ViewType in supported_view_types:
                return v
            else:
                output_stream.write("[WARNING] View '{}' found but its type ({}) is not typically supported for linked view settings.\n".format(name, v.ViewType))
                return None
    return None

def get_link_instance_by_name(doc, name):
    """
    Retrieves a RevitLinkInstance and its associated LinkDocument by the link's title.
    """
    for inst in FilteredElementCollector(doc).OfClass(RevitLinkInstance):
        link_doc = inst.GetLinkDocument()
        if link_doc and link_doc.Title == name:
            return inst, link_doc
    return None, None

def get_linked_view_by_name(link_doc, name):
    """
    Retrieves a view from a linked document by its name.
    Returns (View, suggestions_list).
    """
    all_linked_views = list(FilteredElementCollector(link_doc).OfClass(View))
    
    # 1. Exact Match
    for v in all_linked_views:
        if v.Name == name and not v.IsTemplate:
            return v, []
            
    # 2. Fuzzy/Suggested Match
    suggestions = []
    lower_name = name.lower()
    for v in all_linked_views:
        if not v.IsTemplate:
            if lower_name in v.Name.lower() or v.Name.lower() in lower_name:
                 suggestions.append(v.Name)
    
    return None, suggestions

def process_csv(file_path):
    """
    Reads the CSV file with robust handling (BOM, whitespace),
    processes each row, and attempts to set linked views.
    """
    errors = []
    success_count = 0

    try:
        with open(file_path, 'r') as csvfile:
            # skipinitialspace helps with entries like " Value"
            reader = csv.DictReader(csvfile, skipinitialspace=True)
            
            # --- Robust Header Handling ---
            # Remove BOM (\ufeff) if present in headers and strip whitespace
            if reader.fieldnames:
                cleaned_fieldnames = [name.strip().lstrip('\xef\xbb\xbf') for name in reader.fieldnames]
                reader.fieldnames = cleaned_fieldnames

            expected_headers = ["Host View Name", "Link Name", "Linked View Name"]
            
            # Verify headers exist
            if not all(header in reader.fieldnames for header in expected_headers):
                error_msg = "CSV missing headers. Found: {}. Required: {}.".format(reader.fieldnames, ", ".join(expected_headers))
                WinForms.MessageBox.Show(error_msg, "CSV Format Error", WinForms.MessageBoxButtons.OK, WinForms.MessageBoxIcon.Error)
                output_stream.write("[ERROR] {}\n".format(error_msg))
                return

            # Process Rows
            for row_index, raw_row in enumerate(reader):
                # Clean up values (strip whitespace)
                row = {k: v.strip() for k, v in raw_row.items() if v is not None}
                
                output_stream.write("[INFO] Processing Row {}: {}\n".format(row_index + 2, row))

                host_view_name = row.get("Host View Name")
                link_name = row.get("Link Name")
                linked_view_name = row.get("Linked View Name")

                if not host_view_name or not link_name or not linked_view_name:
                    error_msg = "Row {} is missing required data. Skipping.".format(row_index + 2)
                    errors.append(error_msg)
                    output_stream.write("[ERROR] {}\n".format(error_msg))
                    continue

                # 1. Find Host View
                host_view = get_view_by_name(doc, host_view_name)
                if not host_view:
                    error_msg = "Host view '{}' not found.".format(host_view_name)
                    errors.append(error_msg)
                    output_stream.write("[ERROR] {}\n".format(error_msg))
                    continue

                # Check for View Template
                if host_view.ViewTemplateId != ElementId.InvalidElementId:
                    output_stream.write("[WARNING] Host view '{}' has a View Template assigned. Visual overrides might be locked by the template.\n".format(host_view_name))

                # 2. Find Link Instance
                link_inst, link_doc = get_link_instance_by_name(doc, link_name)
                if not link_inst or not link_doc:
                    error_msg = "Link instance '{}' not found.".format(link_name)
                    errors.append(error_msg)
                    output_stream.write("[ERROR] {}\n".format(error_msg))
                    continue

                # 3. Find Linked View (with fuzzy fallback)
                linked_view, suggestions = get_linked_view_by_name(link_doc, linked_view_name)
                
                if not linked_view:
                    # if suggestions:
                    #     # Auto-select best match
                    #     suggestion = suggestions[0]
                    #     output_stream.write("[WARNING] Linked view '{}' not found. Auto-selecting similar view: '{}'.\n".format(linked_view_name, suggestion))
                    #     linked_view, _ = get_linked_view_by_name(link_doc, suggestion)
                    
                    if not linked_view:
                        error_msg = "Linked view '{}' not found in link '{}'.".format(linked_view_name, link_name)
                        if suggestions:
                            error_msg += " Suggestions: {}.".format(", ".join(suggestions[:3]))
                        errors.append(error_msg)
                        output_stream.write("[ERROR] {}\n".format(error_msg))
                        continue

                # 4. Apply Setting
                # 4. Apply Setting
                # Use RevitLinkGraphicsSettings to set the linked view
                t = Transaction(doc, "Set Linked View")
                try:
                    t.Start()
                    
                    # Create graphics settings
                    graphics_settings = RevitLinkGraphicsSettings()
                    # 1. Set the Visibility Type to 'ByLinkView' FIRST
                    graphics_settings.LinkVisibilityType = LinkVisibility.ByLinkView
                    # 2. Then assign the View ID
                    graphics_settings.LinkedViewId = linked_view.Id
                    
                    # Apply overrides to the host view for this link instance
                    host_view.SetLinkOverrides(link_inst.Id, graphics_settings)
                    
                    t.Commit()
                    output_stream.write("[SUCCESS] Set linked view for '{}' to '{}'.\n".format(host_view_name, linked_view.Name))
                    success_count += 1
                except Exception as e:
                    if t.GetStatus() == TransactionStatus.Started:
                        t.RollBack()
                    error_msg = "Failed to set view: {}".format(str(e))
                    errors.append(error_msg)
                    output_stream.write("[ERROR] {}\n".format(error_msg))

    except Exception as e:
        WinForms.MessageBox.Show("Error reading CSV: {}".format(str(e)), "Error", WinForms.MessageBoxButtons.OK, WinForms.MessageBoxIcon.Error)
        return

    # Final Summary
    if errors:
        WinForms.MessageBox.Show(
            "Completed with {} success(es) and {} error(s).\nCheck console for details.".format(success_count, len(errors)),
            "Completed with Errors",
            WinForms.MessageBoxButtons.OK,
            WinForms.MessageBoxIcon.Warning
        )
    else:
        WinForms.MessageBox.Show(
            "All {} views processed successfully!".format(success_count),
            "Success",
            WinForms.MessageBoxButtons.OK,
            WinForms.MessageBoxIcon.Information
        )

def main():
    file_path = select_csv_file()
    if file_path:
        process_csv(file_path)

if __name__ == "__main__":
    main()
