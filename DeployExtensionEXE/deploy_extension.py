import os
import shutil
import sys
import zipfile
import ctypes  # For user prompt
import pyperclip  # Handles clipboard functionality
import urllib.request  # To download the zip file

# Define the GitHub repository URL (download the latest zip)
github_zip_url = "https://github.com/ArbelTal/pyTal/archive/refs/heads/master.zip"

# Define the destination pyRevit extensions folder
user_profile = os.getenv('USERPROFILE')  # Fetch the user's home directory
pyrevit_extensions_folder = os.path.join(user_profile, "AppData", "Roaming", "pyRevit", "extensions")
destination_folder_name = "pyTal.extension"

# Function to show a message box to the user
def user_prompt(message):
    ctypes.windll.user32.MessageBoxW(0, message, "Deployment Status", 0)


# Function to deploy the extension by downloading and extracting the GitHub repo zip
def deploy_extension():
    try:
        # Check if the target pyRevit extensions folder exists, if not, create it
        if not os.path.exists(pyrevit_extensions_folder):
            os.makedirs(pyrevit_extensions_folder)

        # Define destination path inside the pyRevit extensions folder
        destination_folder = os.path.join(pyrevit_extensions_folder, destination_folder_name)

        # If the folder already exists, remove it first (optional)
        if os.path.exists(destination_folder):
            shutil.rmtree(destination_folder)

        # Use a temporary directory in the user's profile to avoid permission issues
        temp_dir = os.path.join(user_profile, "temp_pyRevit")
        if not os.path.exists(temp_dir):
            os.makedirs(temp_dir)

        # Define paths for zip file and extraction folder
        zip_file_path = os.path.join(temp_dir, "pyTal.zip")

        # Download the zip file from GitHub
        print(f"Downloading zip file from {github_zip_url} to {zip_file_path}...")
        urllib.request.urlretrieve(github_zip_url, zip_file_path)
        print(f"Zip file downloaded: {zip_file_path}")

        # Extract the downloaded zip file
        print(f"Extracting zip file...")
        with zipfile.ZipFile(zip_file_path, 'r') as zip_ref:
            zip_ref.extractall(temp_dir)

        # Check what was extracted
        extracted_files = os.listdir(temp_dir)
        print(f"Extracted files: {extracted_files}")

        # Dynamically detect the extracted folder (GitHub appends branch name to the folder)
        extracted_folder_name = None
        for name in extracted_files:
            full_path = os.path.join(temp_dir, name)
            if os.path.isdir(full_path) and name.startswith('pyTal'):
                extracted_folder_name = name
                break

        if not extracted_folder_name:
            raise FileNotFoundError(f"No extracted folder matching 'pyTal' found in {temp_dir}")

        extract_folder_path = os.path.join(temp_dir, extracted_folder_name)

        # Move the extracted folder to the pyRevit extensions folder
        print(f"Moving extracted folder {extract_folder_path} to {destination_folder}...")
        shutil.move(extract_folder_path, destination_folder)

        # Cleanup: Remove the zip file and temporary extracted folder
        os.remove(zip_file_path)
        shutil.rmtree(temp_dir, ignore_errors=True)
        print("Cleanup completed.")

        # Copy the pyRevit extensions folder path to clipboard
        pyperclip.copy(pyrevit_extensions_folder)

        # Show success message and prompt user
        success_message = (
            f"Extension deployed successfully from GitHub to: {destination_folder}\n\n"
            f"The pyRevit extensions folder path has been copied to your clipboard.\n"
            "You can paste it (Ctrl+V) where needed."
        )
        user_prompt(success_message)

    except Exception as e:
        error_message = f"An error occurred: {str(e)}"
        print(error_message)
        user_prompt(error_message)
        sys.exit(1)


if __name__ == "__main__":
    deploy_extension()
