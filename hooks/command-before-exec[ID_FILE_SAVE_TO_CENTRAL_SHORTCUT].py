# -*- coding: utf-8 -*-
#Imports
from pyrevit import revit, EXEC_PARAMS
from Autodesk.Revit.UI import TaskDialog

#Variables
sender = __eventsender__ # UIApplication
args   = __eventargs__ # Autodesk.UI.Events.BeforeExecutedEventArgs

doc = revit.doc

if not doc. IsFamilyDocument:
    #Show Warning
    TaskDialog.Show('Big Brother is Watching!',
                    'Synchronize NOW is not Allowed! use Synchronize And Modify Settings Instead.')

    # Ask User for Password
    from pyrevit.forms import ask_for_string
    password   = 'sync'
    user_input = ask_for_string(prompt='Only users with password can use Synchronize NOW',
                                title='Synchronize NOW Blocked')

    #Stop Execution
    if user_input != password:
        args.Cancel = True
        TaskDialog.Show('Wrong password!',
                        'operation terminated!')
    else:
        TaskDialog.Show('Synchronize NOW',
                        'Synchronize NOW!')