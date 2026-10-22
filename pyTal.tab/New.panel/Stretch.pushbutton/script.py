# -*- coding: utf-8 -*-
"""
Stretch 2D Lines - מתיחת קווי דו-ממד
תומך בהתנהגות Directional:
1. גרירה מימין לשמאל: מסגרת מקווקוות (Crossing) - מותח קו גם אם רק קצה אחד שלו נבחר (הקצה השני נשאר במקום).
2. גרירה משמאל לימין: מסגרת קו שלם (Window) - מותח/מזיז את הקו רק אם כולו נבחר (2 הקצוות בתוך החלון).
"""

from pyrevit import revit, DB, UI, forms
from Autodesk.Revit.UI.Selection import PickBoxStyle
from Autodesk.Revit.Exceptions import OperationCanceledException


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


def is_right_to_left_drag(picked_box, active_view, uidoc):
    """
    מזהה האם הגרירה בוצעה מימין לשמאל (Crossing) או משמאל לימין (Window).
    """
    origin = active_view.Origin
    right_dir = active_view.RightDirection
    up_dir = active_view.UpDirection

    # בדיקה ראשונית: האם Min ו-Max מוחזרים בסדר הלחיצות המקורי
    u_min_raw, _ = to_view_coords(picked_box.Min, origin, right_dir, up_dir)
    u_max_raw, _ = to_view_coords(picked_box.Max, origin, right_dir, up_dir)

    if u_min_raw > u_max_raw:
        return True

    # בדיקה משנית מדויקת: מיקום סמן העכבר במסך ברגע סיום הגרירה
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

                # אם העכבר בצד שמאל של מרכז המלבן -> גרירה מימין לשמאל (Crossing)
                return mouse_screen_x < screen_center_x
    except Exception:
        pass

    return False


def main():
    doc = revit.doc
    uidoc = revit.uidoc
    active_view = doc.ActiveView

    # בדיקה שהמבט הפעיל תומך בציור/עריכת קווי 2D
    invalid_types = [
        DB.ViewType.ThreeD,
        DB.ViewType.Walkthrough,
        DB.ViewType.DrawingSheet,
        DB.ViewType.Schedule
    ]
    if active_view.ViewType in invalid_types:
        return

    # שלב 1: בחירת מלבן באמצעות PickBoxStyle.Directional
    # מימין לשמאל: מסגרת מקווקוות (Crossing)
    # משמאל לימין: מסגרת קו שלם (Window)
    try:
        picked_box = uidoc.Selection.PickBox(
            PickBoxStyle.Directional,
            "גרור מלבן בחירה: מימין לשמאל (מקווקו / Crossing) או משמאל לימין (שלם / Window)"
        )
    except Exception:
        return

    if not picked_box:
        return

    # זיהוי כיוון הגרירה: מימין לשמאל (Crossing) או משמאל לימין (Window)
    is_crossing = is_right_to_left_drag(picked_box, active_view, uidoc)

    # חישוב גבולות המלבן במערכת הצירים של המבט הנוכחי
    origin = active_view.Origin
    right_dir = active_view.RightDirection
    up_dir = active_view.UpDirection

    u1, v1 = to_view_coords(picked_box.Min, origin, right_dir, up_dir)
    u2, v2 = to_view_coords(picked_box.Max, origin, right_dir, up_dir)

    u_min, u_max = min(u1, u2), max(u1, u2)
    v_min, v_max = min(v1, v2), max(v1, v2)

    # איסוף כל קווי ה-2D (Detail Lines) וה-CurveElements במבט הפעיל
    curve_filter = DB.CurveElementFilter(DB.CurveElementType.Invalid, True)
    collector = (
        DB.FilteredElementCollector(doc, active_view.Id)
        .WherePasses(curve_filter)
        .WhereElementIsNotElementType()
    )

    lines_to_stretch = []

    for elem in collector:
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
            # 1. מימין לשמאל (Crossing): נמתח גם אם נבחר רק חלק מהקו (קצה אחד)
            if in_0 or in_1:
                lines_to_stretch.append({
                    "elem": elem,
                    "curve": geom_curve,
                    "move_0": in_0,
                    "move_1": in_1,
                    "pt0": pt0,
                    "pt1": pt1
                })
        else:
            # 2. משמאל לימין (Window): נמתח אך ורק אם הקו נבחר במלואו (2 הקצוות בתוך החלון)
            if in_0 and in_1:
                lines_to_stretch.append({
                    "elem": elem,
                    "curve": geom_curve,
                    "move_0": True,
                    "move_1": True,
                    "pt0": pt0,
                    "pt1": pt1
                })

    if not lines_to_stretch:
        return

    # שלב 2: בחירת נקודת בסיס ונקודת יעד לקביעת כיוון ומרחק המתיחה
    try:
        base_point = uidoc.Selection.PickPoint(
            "בחר נקודת בסיס למתיחה (Base Point)"
        )
        target_point = uidoc.Selection.PickPoint(
            "בחר נקודת יעד חדשה (Target Point)"
        )
    except Exception:
        return

    delta = target_point - base_point

    if delta.GetLength() < 0.0001:
        return

    short_curve_tol = doc.Application.ShortCurveTolerance

    # שלב 3: ביצוע המתיחה בתוך Transaction
    with revit.Transaction("Stretch 2D Lines"):
        for item in lines_to_stretch:
            elem = item["elem"]
            new_pt0 = item["pt0"] + delta if item["move_0"] else item["pt0"]
            new_pt1 = item["pt1"] + delta if item["move_1"] else item["pt1"]

            if new_pt0.DistanceTo(new_pt1) < short_curve_tol:
                continue

            try:
                new_line = DB.Line.CreateBound(new_pt0, new_pt1)
                if hasattr(elem, "SetGeometryCurve"):
                    elem.SetGeometryCurve(new_line, True)
                else:
                    elem.GeometryCurve = new_line
            except Exception:
                continue


if __name__ == "__main__":
    main()
