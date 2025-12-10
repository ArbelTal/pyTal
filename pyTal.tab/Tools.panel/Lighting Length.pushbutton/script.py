# -*- coding: utf-8 -*-
import math
from Autodesk.Revit.DB import *
from pyrevit import script

# --- הגדרת משתנים ---
doc = __revit__.ActiveUIDocument.Document
output = script.get_output()

# שמות הפרמטרים
len_param_name = "SN_Length"
# נבדוק שני שמות אפשריים של הפרמטר הסידורי (Type/Instance)
serial_param_names = ["SN_Lighting Serial Number", "SN_Light Serial Number"]

# מילונים לאגירת נתונים
data_dict = {}   # מפתח: שם טיפוס, ערך: אורך מצטבר בס"מ
serial_dict = {} # מפתח: שם טיפוס, ערך: מספר סידורי

# --- פונקציות עזר (אותה לוגיקה חזקה כמו קודם) ---

def get_param_value_string(elem, p_name):
    """שליפת מספר סידורי (טקסט)"""
    val = ""
    p = elem.LookupParameter(p_name)
    if not p:
        for param in elem.Parameters:
            if param.Definition.Name.lower() == p_name.lower():
                p = param
                break
    
    if p and p.HasValue:
        val = p.AsString()
        if not val:
            # לעיתים ערך מוצג רק דרך ValueString (לדוגמה Shared Params)
            try:
                val = p.AsValueString()
            except:
                val = ""
        if not val: 
            if p.StorageType == StorageType.Double:
                val = str(round(p.AsDouble(), 2))
            elif p.StorageType == StorageType.Integer:
                val = str(p.AsInteger())
    return val

def get_length_val_cm(elem, p_name):
    """שליפת אורך והמרה מרגל (Feet) לסנטימטר"""
    val_cm = 0.0
    p = elem.LookupParameter(p_name)
    
    if not p:
        for param in elem.Parameters:
            if param.Definition.Name.lower() == p_name.lower():
                p = param
                break
                
    if p and p.HasValue:
        if p.StorageType == StorageType.Double:
            # המרה: 1 רגל = 30.48 ס"מ
            val_cm = p.AsDouble() * 30.48
        elif p.StorageType == StorageType.Integer:
            val_cm = float(p.AsInteger())
        elif p.StorageType == StorageType.String:
            try:
                val_cm = float(p.AsString())
            except:
                val_cm = 0
    return val_cm

# --- ביצוע הסריקה ---
output.print_md("### 🚀 מחשב אורך גופי תאורה...")

collector = FilteredElementCollector(doc)\
            .OfCategory(BuiltInCategory.OST_LightingFixtures)\
            .WhereElementIsNotElementType()\
            .ToElements()

count_processed = 0

for element in collector:
    try:
        # 1. שליפת אורך
        current_len = get_length_val_cm(element, len_param_name)
        
        if current_len > 0.01:
            count_processed += 1
            
            # 2. זיהוי שם הטיפוס
            key_name = element.Name
            elem_type = None
            try:
                type_id = element.GetTypeId()
                elem_type = doc.GetElement(type_id)
                if elem_type:
                    key_name = "{} : {}".format(elem_type.FamilyName, elem_type.Name)
            except:
                pass

            # 3. צבירת אורך
            if key_name in data_dict:
                data_dict[key_name] += current_len
            else:
                data_dict[key_name] = current_len

            # 4. שליפת מספר סידורי (רק פעם אחת לכל טיפוס)
            if key_name not in serial_dict:
                serial_val = ""
                # בדיקה בשני שמות אפשריים, תחילה ב-Type ואז ב-Instance
                for p_name in serial_param_names:
                    if elem_type and not serial_val:
                        t_val = get_param_value_string(elem_type, p_name)
                        if t_val:
                            serial_val = t_val
                            break
                    if not serial_val:
                        i_val = get_param_value_string(element, p_name)
                        if i_val:
                            serial_val = i_val
                            break
                
                serial_dict[key_name] = serial_val

    except Exception:
        pass

# --- יצירת הטבלה לפלט ---

table_data = []

# מיון המפתחות לפי א-ב
sorted_keys = sorted(data_dict.keys())

for name in sorted_keys:
    total_cm = data_dict[name]
    
    # החישוב שלך: חלוקה ב-100 ועיגול למעלה
    final_meters = int(math.ceil(total_cm / 100))
    
    serial_num = serial_dict.get(name, "---")
    if not serial_num: serial_num = "---"
    
    # הוספת שורה לטבלה
    table_data.append([name, serial_num, final_meters])

# --- הדפסה למסך ---
if len(table_data) > 0:
    output.print_md("## ✅ סיכום אורכי גופי תאורה")
    output.print_md("נמצאו **{}** גופים רלוונטיים.".format(count_processed))
    
    # הדפסת טבלה מעוצבת
    output.print_table(
        table_data=table_data,
        columns=["Family & Type", "Serial Number", "Total Length (m)"],
        formats=["", "", ""] # ניתן להוסיף פירמוט אם רוצים
    )
else:
    output.print_md("## ⚠️ לא נמצאו נתונים")
    output.print_md("לא נמצאו גופים עם הפרמטר **{}** בעל ערך חיובי.".format(len_param_name))