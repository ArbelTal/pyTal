# -*- coding: utf-8 -*-
"""
מעביר אביזרים/מעגלים ללוח חשמל אחר ושומר על המיקום (מספר המעגל) שלהם.
"""
from pyrevit import revit, DB, forms

doc = revit.doc

def move_circuits_keep_slots():
    # 1. קבלת כל הלוחות בפרויקט
    panels = DB.FilteredElementCollector(doc).OfCategory(DB.BuiltInCategory.OST_ElectricalEquipment)\
               .WhereElementIsNotElementType().ToElements()
    
    class PanelOption(forms.TemplateListItem):
        @property
        def name(self):
            panel_name = self.item.get_Parameter(DB.BuiltInParameter.RBS_ELEC_PANEL_NAME)
            p_name_str = panel_name.AsString() if panel_name else "Unnamed"
            return "{} (ID: {})".format(p_name_str, self.item.Id)

    panel_options = [PanelOption(p) for p in panels]
    panel_options.sort(key=lambda x: x.name)
    
    # 2. בחירת לוח מקור
    selected_source_item = forms.SelectFromList.show(
        panel_options,
        title="Select the source electrical panel",
        button_name="Select Source Panel"
    )

    if not selected_source_item:
        return # המשתמש ביטל

    source_panel = getattr(selected_source_item, 'item', selected_source_item)
    
    # 3. חילוץ המעגלים מלוח המקור
    if not hasattr(source_panel, 'MEPModel') or not source_panel.MEPModel:
        forms.alert("Cannot extract circuits from this panel.", exitscript=True)
        return
        
    assigned_systems = source_panel.MEPModel.GetAssignedElectricalSystems()
    if not assigned_systems:
        forms.alert("No circuits assigned to this panel were found.", exitscript=True)
        return
        
    class CircuitOption(forms.TemplateListItem):
        @property
        def name(self):
            circuit_number = self.item.CircuitNumber
            load_name = self.item.LoadName
            return "Circuit {} - {}".format(circuit_number, load_name)

    circuit_options = [CircuitOption(c) for c in assigned_systems]
    # מיון לפי מספר המעגל או המיקום
    circuit_options.sort(key=lambda x: x.item.StartSlot if hasattr(x.item, 'StartSlot') else 0)
    
    # 4. בחירת מעגלים להעברה
    selected_circuit_items = forms.SelectFromList.show(
        circuit_options,
        title="Select the circuits you want to move",
        button_name="Select Circuits",
        multiselect=True
    )
    
    if not selected_circuit_items:
        return
        
    circuits_to_move = [getattr(c, 'item', c) for c in selected_circuit_items]
    
    # 5. בחירת לוח יעד
    # נסנן את לוח המקור מתוך רשימת לוחות היעד
    target_panel_options = [p for p in panel_options if p.item.Id != source_panel.Id]
    
    selected_target_item = forms.SelectFromList.show(
        target_panel_options,
        title="Select the target electrical panel",
        button_name="Select Target Panel"
    )

    if not selected_target_item:
        return

    target_panel = getattr(selected_target_item, 'item', selected_target_item)

    # 4. ביצוע ההעברה בתוך Transaction
    with revit.Transaction("Move circuits and keep slots"):
        
        # בדיקה אם ללוח היעד יש כבר Schedule (חובה כדי שנוכל להזיז בתוכו מיקומים)
        psv = None
        for view in DB.FilteredElementCollector(doc).OfClass(DB.Electrical.PanelScheduleView):
            if view.GetPanel() == target_panel.Id:
                psv = view
                break
        
        # אם אין ללוח Schedule, ניצור אחד זמני כדי שנוכל למקם את המעגלים בתוכו
        if not psv:
            try:
                psv = DB.Electrical.PanelScheduleView.CreateInstanceView(doc, target_panel.Id)
            except Exception as e:
                print("Cannot create Panel Schedule for the target panel.")

        moved_count = 0
        errors = []
        for circuit in circuits_to_move:
            old_slot = circuit.StartSlot
            circuit_num = circuit.CircuitNumber
            
            # ניתוק מהלוח הישן וחיבור ללוח החדש
            try:
                circuit.SelectPanel(target_panel)
                doc.Regenerate() # חובה כדי שהמיקום החדש יתעדכן לפני בדיקת המיקומים
            except Exception as e:
                errors.append("Error moving circuit {}: {}".format(circuit_num, e))
                continue
                
            if not psv or old_slot <= 0:
                moved_count += 1
                if not psv:
                    errors.append("Target panel has no Panel Schedule; circuit {} could not keep its slot.".format(circuit_num))
                continue
                
            new_slot = circuit.StartSlot
            
            # אם המיקום החדש שונה מהמיקום המקורי, ננסה להזיז אותו בחזרה
            if old_slot != new_slot:
                try:
                    # הפונקציה מחזירה שתי רשימות (שורות ועמודות)
                    rows_new, cols_new = psv.GetCellsBySlotNumber(new_slot)
                    rows_old, cols_old = psv.GetCellsBySlotNumber(old_slot)
                    
                    r1, c1 = rows_new[0], cols_new[0]
                    r2, c2 = rows_old[0], cols_old[0]
                    
                    # בדיקה האם המעבר אפשרי והזזת המעגל חזרה למיקום (Slot) הקודם
                    if psv.CanMoveSlotTo(r1, c1, r2, c2):
                        psv.MoveSlotTo(r1, c1, r2, c2)
                    else:
                        errors.append("Circuit {} moved, but slot {} on the target panel is occupied or unavailable.".format(circuit_num, old_slot))
                except Exception as e:
                    errors.append("Circuit {} moved, but an error prevented keeping slot {}: {}".format(circuit_num, old_slot, e))
            
            moved_count += 1
            
    if errors:
        forms.alert("Some operations encountered errors:\n\n" + "\n".join(errors), title="Completed with Warnings")
    else:
        forms.alert("Successfully moved {} circuits to panel: {}".format(moved_count, target_panel.Name), title="Completed Successfully")

# הרצת הפונקציה
if __name__ == '__main__':
    move_circuits_keep_slots()
