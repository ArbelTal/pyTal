import os
import shutil
import sys
import tempfile
import pyperclip  # Handles clipboard functionality
import ctypes     # For user prompt

# Define the destination pyRevit extensions folder
user_profile = os.getenv('USERPROFILE')  # Fetch the user's home directory
pyrevit_extensions_folder = os.path.join(user_profile, "AppData", "Roaming", "pyRevit", "Extensions")
destination_folder_name = "ArbelExtension.extension"

# Function to show a message box to the user
def user_prompt(message):
    ctypes.windll.user32.MessageBoxW(0, message, "Deployment Status", 0)

# Function to copy the extension folder
def deploy_extension():
    try:
        # Use a temporary directory to extract the bundled extension files
        temp_dir = tempfile.mkdtemp()

        # PyInstaller places bundled data in a temporary directory
        if hasattr(sys, '_MEIPASS'):
            # Path to the folder inside the .exe (bundled via PyInstaller)
            source_folder = os.path.join(sys._MEIPASS, destination_folder_name)
        else:
            # Fallback in case running from script, for testing purposes
            source_folder = os.path.join(os.getcwd(), destination_folder_name)

        # Check if the target pyRevit extensions folder exists, if not, create it
        if not os.path.exists(pyrevit_extensions_folder):
            os.makedirs(pyrevit_extensions_folder)

        # Define destination path inside the pyRevit extensions folder
        destination_folder = os.path.join(pyrevit_extensions_folder, destination_folder_name)

        # If the folder already exists, remove it first (optional)
        if os.path.exists(destination_folder):
            shutil.rmtree(destination_folder)

        # Copy the bundled extension folder to the destination
        shutil.copytree(source_folder, destination_folder)

        # Copy the pyRevit extensions folder path to clipboard
        pyperclip.copy(pyrevit_extensions_folder)

        # Show success message and prompt user
        success_message = (
            f"Extension deployed successfully to: {destination_folder}\n\n"
            f"The pyRevit extensions folder path has been copied to your clipboard.\n"
            "You can paste it (Ctrl+V) where needed."
        )
        user_prompt(success_message)

    except Exception as e:
        error_message = f"An error occurred: {str(e)}"
        user_prompt(error_message)
        sys.exit(1)

if __name__ == "__main__":
    deploy_extension()

