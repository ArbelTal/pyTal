"""Create worksets from a list and set defautl visibility"""
# -*- coding: utf-8 -*-
__title__   = "Create worksets"
__doc__     = """Version = 1.0
Date    = 01.10.2024
________________________________________________________________
Description:
Create Worksets from CSV file. 
________________________________________________________________
How-To:
1. Create or pick CSV file.
2. The CSV should contain at least one column "WorksetName".
   Other columns are optional.
________________________________________________________________
TODO:
________________________________________________________________
Last Updates:
- [01.10.2024] v1.0 Change Description
________________________________________________________________
Author: Arbel Tal"""

from Autodesk.Revit.DB import *
from Autodesk.Revit.UI import *
from Autodesk.Revit import DB

from pyrevit import forms

import csv



uidoc = __revit__.ActiveUIDocument
doc = __revit__.ActiveUIDocument.Document




def set_workset_default_visiblity(d, workset, state):
    wdvs = DB.WorksetDefaultVisibilitySettings.GetWorksetDefaultVisibilitySettings(d)
    wdvs.SetWorksetVisibility(workset.Id, state)


def create_workset(d, name):
    return DB.Workset.Create(d, name)


def read_csv(path):
	"""
    read csv column into list
    param path= Path to csv file
    
    """

	with open(path, 'r') as csvfile:
		reader = csv.DictReader(csvfile)
		mylist = []

		for row in reader:
			mylist.append(row["WorksetName"]) 
        return mylist


path = forms.pick_file(file_ext='csv', files_filter='', init_dir='', restore_dir=True, multi_file=False, unc_paths=False, title='Select csv worksets file')

workset_names = read_csv(path)


if doc.IsWorkshared:
    t = DB.Transaction(doc, "Create Worksets")
    t.Start()

    # make your model changes here
    for name in workset_names:
      ws = create_workset(doc, name)
      if "Hidden" in name:
         set_workset_default_visiblity(doc, ws, False)

    t.Commit()