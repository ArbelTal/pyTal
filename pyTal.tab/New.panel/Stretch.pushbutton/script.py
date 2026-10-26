# -*- coding: utf-8 -*-
"""‏Stretch 2D Elements - מתיחת אלמנטי דו-ממד‏

‏מתיחת קווי דו-ממד, רכיבי פרט (Detail Items) וסימונים (Generic Annotations)‏

‏הוראות שימוש:‏
‏שלב א - בחירת חלון סביב האלמנטים:‏
‏• גרירה מימין לשמאל (Crossing): מותח קווים ורכיבים גם אם נבחר רק קצה אחד. מזיז משפחות שנוגעות בחלון.‏
‏• גרירה משמאל לימין (Window): מותח אך ורק אלמנטים שנבחרו במלואם בתוך החלון.‏

‏שלב ב - בחירת נקודת בסיס (Base Point) למתיחה.‏
‏שלב ג - בחירת נקודת יעד חדשה (Target Point).‏

‏מצב קו ישר (Ortho / F8):‏
‏• מקש Shift + קליק על הכפתור בריבון: פתיחת הגדרות לבחירת מצב F8 כברירת מחדל (האייקון הופך לכתום!).‏
‏• החזקת מקש Shift בעת בחירת נקודת היעד: נועלת לקו ישר (אופקי/אנכי) או משחררת למצב חופשי.‏
"""
from pyrevit import revit, DB, forms, script, EXEC_PARAMS
from Autodesk.Revit.UI.Selection import PickBoxStyle
from Autodesk.Revit.Exceptions import OperationCanceledException
from System.Collections.Generic import List


def get_ortho_setting():
    """קריאת הגדרת מצב Ortho מתוך ה-Config של pyRevit."""
    try:
        cfg = script.get_config()
        return getattr(cfg, "ortho_mode", False)
    except Exception:
        return False


def set_ortho_setting(value):
    """שמירת הגדרת מצב Ortho לתוך ה-Config של pyRevit."""
    try:
        cfg = script.get_config()
        cfg.ortho_mode = value
        script.save_config()
    except Exception:
        pass


def update_button_icon(is_ortho):
    """
    מעדכן את צבע האייקון בריבון:
    - כתום במצב F8 / Ortho פעיל (on.png)
    - שחור רגיל במצב חופשי (icon.png)
    """
    try:
        import os.path as op
        cmd_dir = op.dirname(__file__)
        on_icon = op.join(cmd_dir, "on.png")
        off_icon = op.join(cmd_dir, "icon.png")
        script.toggle_icon(is_ortho, on_icon_path=on_icon, off_icon_path=off_icon)
    except Exception:
        try:
            script.toggle_icon(is_ortho)
        except Exception:
            pass


def is_shift_pressed():
    """
    בודק האם מקש Shift לחוץ בעת בחירת הנקודה (לשינוי מצב Ortho בזמן אמת).
    """
    try:
        from System.Windows.Forms import Control, Keys
        if bool(Control.ModifierKeys & Keys.Shift):
            return True
    except Exception:
        pass

    try:
        import ctypes
        if (ctypes.windll.user32.GetAsyncKeyState(0x10) & 0x8000) != 0:
            return True
    except Exception:
        pass

    return False


def get_id_val(elem_id):
    """
    מחזיר את הערך המספרי של ElementId בתאימות לכל גרסאות Revit.
    (ב-Revit 2024 ומטה: IntegerValue, ב-Revit 2025 ומעלה: Value).
    """
    if hasattr(elem_id, "Value"):
        return elem_id.Value
    if hasattr(elem_id, "IntegerValue"):
        return elem_id.IntegerValue
    return int(elem_id)


def to_view_coords(point, origin, right_dir, up_dir):
    """
    מחשב היטל של נקודה תלת-ממדית על מערכת הצירים של המבט הדו-ממדי.
    """
    diff = point - origin
    u = diff.DotProduct(right_dir)
    v = diff.DotProduct(up_dir)
    return u, v


def is_point_in_box(point, u_min, u_max, v_min, v_max, origin, right_dir, up_dir, tol=0.005):
    """
    בודק האם נקודה נמצאת בתוך גבולות המלבן שנבחר במבט.
    """
    u, v = to_view_coords(point, origin, right_dir, up_dir)
    return (u_min - tol <= u <= u_max + tol) and (v_min - tol <= v <= v_max + tol)


def is_bbox_in_selection(bbox, u_min, u_max, v_min, v_max, origin, right_dir, up_dir, is_crossing, tol=0.005):
    """
    בודק האם תיבת הגבולות (BoundingBox) של אלמנט נלכדה בחלון הבחירה:
    - במצב Crossing: האם יש חפיפה כלשהי (Overlap / Touch) בין ה-BoundingBox למלבן.
    - במצב Window: האם ה-BoundingBox מוכל במלואו (Fully Enclosed) בתוך המלבן.
    """
    if not bbox:
        return False

    b_u1, b_v1 = to_view_coords(bbox.Min, origin, right_dir, up_dir)
    b_u2, b_v2 = to_view_coords(bbox.Max, origin, right_dir, up_dir)

    b_umin, b_umax = min(b_u1, b_u2), max(b_u1, b_u2)
    b_vmin, b_vmax = min(b_v1, b_v2), max(b_v1, b_v2)

    if is_crossing:
        overlaps_u = not (b_umax < u_min - tol or b_umin > u_max + tol)
        overlaps_v = not (b_vmax < v_min - tol or b_vmin > v_max + tol)
        return overlaps_u and overlaps_v
    else:
        enclosed_u = (u_min - tol <= b_umin) and (b_umax <= u_max + tol)
        enclosed_v = (v_min - tol <= b_vmin) and (b_vmax <= v_max + tol)
        return enclosed_u and enclosed_v


def is_right_to_left_drag(picked_box, active_view, uidoc):
    """
    מזהה האם הגרירה בוצעה מימין לשמאל (Crossing) או משמאל לימין (Window).
    """
    origin = active_view.Origin
    right_dir = active_view.RightDirection
    up_dir = active_view.UpDirection

    u_min_raw, _ = to_view_coords(picked_box.Min, origin, right_dir, up_dir)
    u_max_raw, _ = to_view_coords(picked_box.Max, origin, right_dir, up_dir)

    if u_min_raw > u_max_raw:
        return True

    try:
        from System.Windows.Forms import Cursor
        mouse_screen_x = Cursor.Position.X

        ui_view = None
        for uv in uidoc.GetOpenUIViews():
            if uv.ViewId == active_view.Id:
                ui_view = uv
                break

        if ui_view:
            rect = ui_view.GetWindowRectangle()
            corners = ui_view.GetZoomCorners()

            center_world = 0.5 * (picked_box.Min + picked_box.Max)
            u_center, _ = to_view_coords(center_world, origin, right_dir, up_dir)
            u_corner0, _ = to_view_coords(corners[0], origin, right_dir, up_dir)
            u_corner1, _ = to_view_coords(corners[1], origin, right_dir, up_dir)

            u_left = min(u_corner0, u_corner1)
            u_right = max(u_corner0, u_corner1)
            view_width_u = u_right - u_left

            if view_width_u > 1e-5:
                ratio = (u_center - u_left) / view_width_u
                screen_width = rect.Right - rect.Left
                screen_center_x = rect.Left + ratio * screen_width

                return mouse_screen_x < screen_center_x
    except Exception:
        pass

    return False


def main():
    # סנכרון תצוגת האייקון בריבון למצב הנוכחי
    current_ortho = get_ortho_setting()
    update_button_icon(current_ortho)

    # פתיחת חלון הגדרות ב-Shift+Click על כפתור הכלי ב-Ribbon
    is_config_mode = __shiftclick__ if "__shiftclick__" in globals() else getattr(EXEC_PARAMS, "config_mode", False)
    if is_config_mode:
        opt_free = "מצב חופשי (Free) - מתיחה לכל זווית [איקון שחור]"
        opt_ortho = "מצב F8 (Ortho) - נעילה לקו ישר בלבד [איקון כתום]"
        current_str = opt_ortho if current_ortho else opt_free

        selected = forms.CommandSwitchWindow.show(
            [opt_free, opt_ortho],
            message="הגדרות מצב F8 / Ortho:\nבחר את מצב העבודה (כרגע: {}):".format(current_str)
        )
        if selected:
            new_val = (selected == opt_ortho)
            set_ortho_setting(new_val)
            update_button_icon(new_val)
        return

    doc = revit.doc
    uidoc = revit.uidoc
    active_view = doc.ActiveView

    # בדיקה שהמבט הפעיל תומך בציור/עריכת קווי 2D ופרטים
    invalid_types = [
        DB.ViewType.ThreeD,
        DB.ViewType.Walkthrough,
        DB.ViewType.DrawingSheet,
        DB.ViewType.Schedule
    ]
    if active_view.ViewType in invalid_types:
        return

    # שלב 1: בחירת מלבן באמצעות PickBoxStyle.Directional
    try:
        picked_box = uidoc.Selection.PickBox(
            PickBoxStyle.Directional,
            "גרור מלבן בחירה: מימין לשמאל (מקווקו / Crossing) או משמאל לימין (שלם / Window)"
        )
    except Exception:
        return

    if not picked_box:
        return

    is_crossing = is_right_to_left_drag(picked_box, active_view, uidoc)

    origin = active_view.Origin
    right_dir = active_view.RightDirection
    up_dir = active_view.UpDirection

    u1, v1 = to_view_coords(picked_box.Min, origin, right_dir, up_dir)
    u2, v2 = to_view_coords(picked_box.Max, origin, right_dir, up_dir)

    u_min, u_max = min(u1, u2), max(u1, u2)
    v_min, v_max = min(v1, v2), max(v1, v2)

    lines_to_stretch = []
    instances_to_move = []

    # 1. איסוף קווי 2D
    curve_filter = DB.CurveElementFilter(DB.CurveElementType.Invalid, True)
    curve_elements = (
        DB.FilteredElementCollector(doc, active_view.Id)
        .WherePasses(curve_filter)
        .WhereElementIsNotElementType()
    )

    for elem in curve_elements:
        if elem.Pinned:
            continue

        try:
            geom_curve = elem.GeometryCurve
        except Exception:
            continue

        if not isinstance(geom_curve, DB.Line):
            continue

        pt0 = geom_curve.GetEndPoint(0)
        pt1 = geom_curve.GetEndPoint(1)

        in_0 = is_point_in_box(pt0, u_min, u_max, v_min, v_max, origin, right_dir, up_dir)
        in_1 = is_point_in_box(pt1, u_min, u_max, v_min, v_max, origin, right_dir, up_dir)

        if is_crossing:
            if in_0 or in_1:
                lines_to_stretch.append({
                    "elem": elem,
                    "is_line_instance": False,
                    "move_0": in_0,
                    "move_1": in_1,
                    "pt0": pt0,
                    "pt1": pt1
                })
        else:
            if in_0 and in_1:
                lines_to_stretch.append({
                    "elem": elem,
                    "is_line_instance": False,
                    "move_0": True,
                    "move_1": True,
                    "pt0": pt0,
                    "pt1": pt1
                })

    # 2. איסוף משפחות Detail Items ו-Generic Annotations
    target_category_ids = {
        get_id_val(DB.ElementId(DB.BuiltInCategory.OST_DetailComponents)),
        get_id_val(DB.ElementId(DB.BuiltInCategory.OST_GenericAnnotation))
    }

    family_instances = (
        DB.FilteredElementCollector(doc, active_view.Id)
        .OfClass(DB.FamilyInstance)
        .WhereElementIsNotElementType()
    )

    for inst in family_instances:
        if inst.Pinned:
            continue

        cat = inst.Category
        if not cat or get_id_val(cat.Id) not in target_category_ids:
            continue

        loc = inst.Location

        if isinstance(loc, DB.LocationCurve):
            curve = loc.Curve
            if isinstance(curve, DB.Line):
                pt0 = curve.GetEndPoint(0)
                pt1 = curve.GetEndPoint(1)

                in_0 = is_point_in_box(pt0, u_min, u_max, v_min, v_max, origin, right_dir, up_dir)
                in_1 = is_point_in_box(pt1, u_min, u_max, v_min, v_max, origin, right_dir, up_dir)

                if is_crossing:
                    if in_0 or in_1:
                        lines_to_stretch.append({
                            "elem": inst,
                            "is_line_instance": True,
                            "move_0": in_0,
                            "move_1": in_1,
                            "pt0": pt0,
                            "pt1": pt1
                        })
                else:
                    if in_0 and in_1:
                        lines_to_stretch.append({
                            "elem": inst,
                            "is_line_instance": True,
                            "move_0": True,
                            "move_1": True,
                            "pt0": pt0,
                            "pt1": pt1
                        })

        elif isinstance(loc, DB.LocationPoint):
            loc_pt = loc.Point
            in_pt = is_point_in_box(loc_pt, u_min, u_max, v_min, v_max, origin, right_dir, up_dir)

            bbox = inst.get_BoundingBox(active_view)
            in_bbox = is_bbox_in_selection(
                bbox, u_min, u_max, v_min, v_max, origin, right_dir, up_dir, is_crossing
            )

            if is_crossing:
                if in_bbox or in_pt:
                    instances_to_move.append(inst.Id)
            else:
                if in_bbox or (bbox is None and in_pt):
                    instances_to_move.append(inst.Id)

    if not lines_to_stretch and not instances_to_move:
        return

    # שלב 2: בחירת נקודת בסיס ונקודת יעד לקביעת כיוון ומרחק המתיחה
    base_ortho = get_ortho_setting()
    ortho_hint = "החזק Shift למצב חופשי" if base_ortho else "החזק Shift לקו ישר (Ortho)"

    try:
        base_point = uidoc.Selection.PickPoint(
            "בחר נקודת בסיס למתיחה (Base Point)"
        )
        target_point = uidoc.Selection.PickPoint(
            "בחר נקודת יעד חדשה (Target Point) [{}]".format(ortho_hint)
        )
    except Exception:
        return

    # בדיקה האם מקש Shift לחוץ כעת
    shift_down = is_shift_pressed()

    # אם ברירת המחדל היא Ortho ו-Shift לחוץ -> עובר לחופשי.
    # אם ברירת המחדל היא חופשי ו-Shift לחוץ -> עובר ל-Ortho.
    use_ortho = (not base_ortho) if shift_down else base_ortho

    raw_delta = target_point - base_point

    if use_ortho:
        u = raw_delta.DotProduct(right_dir)
        v = raw_delta.DotProduct(up_dir)

        if abs(u) >= abs(v):
            delta = right_dir.Multiply(u)
        else:
            delta = up_dir.Multiply(v)
    else:
        delta = raw_delta

    if delta.GetLength() < 0.0001:
        return

    short_curve_tol = doc.Application.ShortCurveTolerance

    # שלב 3: ביצוע המתיחה וההזזה בתוך Transaction
    with revit.Transaction("Stretch 2D Elements"):
        for item in lines_to_stretch:
            elem = item["elem"]
            new_pt0 = item["pt0"] + delta if item["move_0"] else item["pt0"]
            new_pt1 = item["pt1"] + delta if item["move_1"] else item["pt1"]

            if new_pt0.DistanceTo(new_pt1) < short_curve_tol:
                continue

            try:
                new_line = DB.Line.CreateBound(new_pt0, new_pt1)
                if item["is_line_instance"]:
                    elem.Location.Curve = new_line
                else:
                    if hasattr(elem, "SetGeometryCurve"):
                        elem.SetGeometryCurve(new_line, True)
                    else:
                        elem.GeometryCurve = new_line
            except Exception:
                continue

        if instances_to_move:
            try:
                ids_collection = List[DB.ElementId](instances_to_move)
                DB.ElementTransformUtils.MoveElements(doc, ids_collection, delta)
            except Exception:
                for inst_id in instances_to_move:
                    try:
                        DB.ElementTransformUtils.MoveElement(doc, inst_id, delta)
                    except Exception:
                        pass


if __name__ == "__main__":
    main()
