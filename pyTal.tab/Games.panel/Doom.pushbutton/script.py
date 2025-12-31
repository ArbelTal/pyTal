
import os
import sys
import subprocess
import os.path as op
from pyrevit import forms

def run_game():
    # Get the path to the current script directory
    current_dir = op.dirname(__file__)
    doom_dir = op.join(current_dir, "DOOM")
    requirements_file = op.join(doom_dir, "requirements.txt")
    main_script = op.join(doom_dir, "main.py")

    if not op.exists(doom_dir):
        forms.alert("DOOM folder not found!", exitscript=True)

    # Use the 'py' launcher to ensure we use a standard Python installation (CPython)
    # instead of IronPython which pyRevit uses.
    python_exe = "py" 

    # 1. Install dependencies
    if op.exists(requirements_file):
        try:
            # Check if pygame is already installed to avoid unnecessary delay/output
            # This is a quick check; pip install will verify versions effectively too.
            with open(os.devnull, 'w') as devnull:
                subprocess.check_call([python_exe, "-c", "import pygame"], cwd=doom_dir, stdout=devnull, stderr=devnull)
        except subprocess.CalledProcessError:
             # If import fails, try to install
            print("Installing dependencies...")
            try:
                subprocess.check_call([python_exe, "-m", "pip", "install", "-r", "requirements.txt"], cwd=doom_dir)
            except subprocess.CalledProcessError as e:
                forms.alert("Failed to install dependencies.\n\nError: {}".format(e))
                return

    # 2. Run the game
    print("Launching DOOM...")
    try:
        subprocess.Popen([python_exe, main_script], cwd=doom_dir)
    except Exception as e:
        forms.alert("Failed to launch game.\n\nError: {}".format(e))

if __name__ == "__main__":
    run_game()
