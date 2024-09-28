import pyrevit
from pyrevit import script, revit, forms
import os

# Set up logger
logger = script.get_logger()

SYNC_VIEW_ENV_VAR = "sync_view_state"  # Name for the environment variable

def get_data_filename(doc):
    """Example function to return a mock file path."""
    return "mock_path_to_data_file"  # Modify this to return the correct data file path


# Function for 'Override Command Off' behavior
def override_cmd_off():
    import state_off
    logger.debug('Override Command: Off')

# Function for 'Override Command On' behavior
def override_cmd_on():
    import state_on
    logger.debug('Override Command: On')


def toggle_state():
    """Toggle tool state"""
    new_state = not script.get_envvar(SYNC_VIEW_ENV_VAR)
    # Remove last data file on start
    if new_state:
        data_filename = get_data_filename(revit.doc)
        if os.path.exists(data_filename):
            os.remove(data_filename)
    script.set_envvar(SYNC_VIEW_ENV_VAR, new_state)
    script.toggle_icon(new_state)  # Toggle the icon based on the state (True/False)


# Main script logic: Check the current toggle state and apply the relevant behavior
toggle_btn_state = script.get_envvar("override_toggle")

if toggle_btn_state == "on":
    # If it's currently "On", turn it "Off"
    override_cmd_off()
    script.set_envvar("override_toggle", "off")
    script.toggle_icon(True, on_icon_path=None, off_icon_path=None)  # Set icon to "off_icon.png"
else:
    # If it's currently "Off", turn it "On"
    override_cmd_on()
    script.set_envvar("override_toggle", "on")
    script.toggle_icon(False, on_icon_path=None, off_icon_path=None)  # Set icon to "on_icon.png"

# Trigger the state toggle
toggle_state()