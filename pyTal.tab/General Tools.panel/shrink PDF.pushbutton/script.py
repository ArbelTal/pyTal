# -*- coding: utf-8 -*-
import os
import sys
import subprocess
from pyrevit import forms, script

__title__ = 'Shrink PDF'
__doc__ = 'Compresses a selected PDF file using PDF24.'

def find_pdf24_doctool():
    """Attempts to find the PDF24 DocTool executable."""
    paths = [
        r"C:\Program Files\PDF24\pdf24-DocTool.exe",
        r"C:\Program Files (x86)\PDF24\pdf24-DocTool.exe",
    ]
    
    for path in paths:
        if os.path.exists(path):
            return path
            
    # Check default install dir if user installed elsewhere
    # (Assuming standard install for now)
    return None

def compress_pdf_pdf24(input_path, output_path, dpi=144, quality=75):
    """Compresses PDF using PDF24 CLI."""
    
    doctool = find_pdf24_doctool()
    if not doctool:
        forms.alert(
            "PDF24 not found.\nPlease install PDF24 Creator or check the installation path.\n(Expected at C:\\Program Files\\PDF24)",
            exitscript=True
        )
        return False
        
    # Command: pdf24-DocTool.exe -compress -dpi 144 -imageQuality 75 -outputFile "output.pdf" "input.pdf"
    cmd = [
        doctool,
        "-compress",
        "-dpi", str(dpi),
        "-imageQuality", str(quality),
        "-outputFile", output_path,
        input_path
    ]
    
    try:
        # Use subprocess to call the exe
        # Shell=True might be needed for some windows execution contexts, but try without first for safety
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        stdout, stderr = process.communicate()
        
        if process.returncode == 0:
            return True
        else:
            print("PDF24 Error: {}".format(stderr))
            return False
            
    except Exception as e:
        print("Error calling PDF24: {}".format(e))
        return False

def main():
    # 1. Pick File
    input_pdf = forms.pick_file(file_ext='pdf', title='Select PDF to Compress')
    if not input_pdf:
        return

    # 2. Configure Quality
    # Map friendly names to (DPI, Quality)
    profiles = {
        "High Quality (Printer)": (300, 90),
        "Standard (Ebook/Office)": (144, 75),
        "Low Quality (Screen/Email)": (72, 60)
    }
    
    selected_name = forms.SelectFromList.show(
        sorted(profiles.keys()),
        title='Select Compression Level',
        button_name='Compress'
    )
    
    if not selected_name:
        return
        
    dpi, quality = profiles[selected_name]

    output_pdf = input_pdf.replace(".pdf", "_compressed.pdf")
    
    print("Compressing: {}...".format(input_pdf))
    print("Using PDF24 (DPI: {}, Quality: {})...".format(dpi, quality))
    
    success = compress_pdf_pdf24(input_pdf, output_pdf, dpi, quality)
    
    if success:
        if os.path.exists(output_pdf):
            old_size = os.path.getsize(input_pdf)
            new_size = os.path.getsize(output_pdf)
            ratio = (1 - (float(new_size) / old_size)) * 100
            
            print("Done! Saved as: {}".format(output_pdf))
            print("Original Size: {:.2f} MB".format(old_size / (1024*1024.0)))
            print("New Size: {:.2f} MB".format(new_size / (1024*1024.0)))
            print("Reduction: {:.1f}%".format(ratio))
        else:
            print("Error: Output file not created. (Check PDF24 installation?)")
    else:
        print("Compression failed.")

if __name__ == '__main__':
    main()

