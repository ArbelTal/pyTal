# Necessary imports
from pyrevit import revit, DB, forms
import clr

# Add reference to PresentationCore for Clipboard functionality
clr.AddReference('PresentationCore')
from System.Windows import Clipboard

# Initialize document
doc = __revit__.ActiveUIDocument.Document


# Function to return the Project Base Point ID
def get_pbp_id(doc):
    # Collect all elements in the Project Base Point category
    base_points = DB.FilteredElementCollector(doc).OfCategory(DB.BuiltInCategory.OST_ProjectBasePoint).WhereElementIsNotElementType().ToElements()

    # Check if any Project Base Points were found
    if base_points:
        # Return the first found Project Base Point ID
        for base_point in base_points:
            return base_point.Id.IntegerValue  # Return the PBP element ID as an integer
    else:
        # If no PBP is found, return None
        return None

# Function to get the Angle to True North for a specific PBP element
def get_pbp_angle_to_true_north(doc, pbp_id):
    # Retrieve the Project Base Point element by its ID
    element_id = DB.ElementId(pbp_id)
    pbp_element = doc.GetElement(element_id)

    if pbp_element:
        # Get the 'Angle to True North' parameter
        angle_param = pbp_element.get_Parameter(DB.BuiltInParameter.BASEPOINT_ANGLETON_PARAM)

        # Check if the angle parameter exists
        if angle_param:
            return angle_param.AsDouble()  # Return the angle in radians
        else:
            return None  # Parameter not found
    else:
        return None  # Project Base Point element not found

# Function to copy PBP angle to clipboard
def copy_pbp_angle_to_clipboard(pbp_angle):
    angle_radians =pbp_angle

    if pbp_angle is not None:
        if angle_radians is not None:
            # Convert the angle from radians to degrees
            #angle_degrees = angle_radians * (180.0 / 3.14159)
            angle_degrees = round(angle_radians * (180.0 / 3.14159),2)

            # Copy the numeric value of the angle (degrees) to the clipboard
            Clipboard.SetText(str(angle_degrees))  # Convert the number to a string before copying

            # Notify the user
            forms.alert("Project Base Point angle to True North copied to clipboard: {}".format(angle_degrees), title="PBP Angle Copied")
        else:
            forms.alert("Could not retrieve the angle to True North.", title="Error")
    else:
        forms.alert("Project Base Point not found.", title="Error")


def my_addin():
    doc = revit.doc
    pbp_id = get_pbp_id(doc)
    pbp_angle = get_pbp_angle_to_true_north(doc, pbp_id)
    copy_pbp_angle_to_clipboard(pbp_angle)


# Run the main function
my_addin()