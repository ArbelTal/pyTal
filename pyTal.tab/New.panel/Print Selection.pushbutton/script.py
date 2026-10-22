# -*- coding: utf-8 -*-
"""
Lets you select an area on the screen and opens the Print dialog 
set to print the visible portion.
"""

import sys
from pyrevit import revit, DB, UI
from pyrevit import forms

import clr
clr.AddReference("PresentationFramework")
clr.AddReference("PresentationCore")
clr.AddReference("WindowsBase")
clr.AddReference("System.Drawing")

import System
from System.Windows import Window, WindowStyle, Visibility, Rect, Point
from System.Windows.Media import Brushes, GeometryGroup, RectangleGeometry, FillRule, Color, SolidColorBrush
from System.Windows.Shapes import Path, Rectangle
from System.Windows.Controls import Canvas, TextBlock
from System.Windows.Input import MouseButtonEventHandler, MouseEventHandler, KeyEventHandler, Key, Cursors

import System.Drawing as Drawing

doc = revit.doc
uidoc = revit.uidoc

class SnippingWindow(Window):
    def __init__(self, rect, scaleX, scaleY):
        self.WindowStyle = WindowStyle.None
        self.AllowsTransparency = True
        self.Background = SolidColorBrush(Color.FromArgb(1, 0, 0, 0)) # Prevent click-through
        self.Topmost = True
        self.ShowInTaskbar = False
        self.Cursor = Cursors.Cross
        
        self.Left = rect.Left / scaleX
        self.Top = rect.Top / scaleY
        self.Width = (rect.Right - rect.Left) / scaleX
        self.Height = (rect.Bottom - rect.Top) / scaleY
        
        self.canvas = Canvas()
        self.canvas.Background = Brushes.Transparent # Crucial for mouse hit testing
        self.Content = self.canvas
        
        self.dimBrush = SolidColorBrush(Color.FromArgb(160, 0, 0, 0)) # Dimmed background
        
        self.rectTop = Rectangle()
        self.rectTop.Fill = self.dimBrush
        self.rectBottom = Rectangle()
        self.rectBottom.Fill = self.dimBrush
        self.rectBottom.Width = self.Width
        self.rectLeft = Rectangle()
        self.rectLeft.Fill = self.dimBrush
        self.rectRight = Rectangle()
        self.rectRight.Fill = self.dimBrush
        
        self.canvas.Children.Add(self.rectTop)
        self.canvas.Children.Add(self.rectBottom)
        self.canvas.Children.Add(self.rectLeft)
        self.canvas.Children.Add(self.rectRight)
        
        self.rectTop.Width = self.Width
        self.rectTop.Height = self.Height
        Canvas.SetLeft(self.rectTop, 0)
        Canvas.SetTop(self.rectTop, 0)
        
        self.selectionRect = Rectangle()
        self.selectionRect.Stroke = Brushes.Red
        self.selectionRect.StrokeThickness = 2
        self.selectionRect.Visibility = Visibility.Hidden
        self.canvas.Children.Add(self.selectionRect)

        self.textBlock = TextBlock()
        self.textBlock.Text = "Select area to print (Press ESC to cancel)"
        self.textBlock.Foreground = Brushes.White
        self.textBlock.FontSize = 20
        self.textBlock.FontWeight = System.Windows.FontWeights.Bold
        Canvas.SetLeft(self.textBlock, 10)
        Canvas.SetTop(self.textBlock, 10)
        self.canvas.Children.Add(self.textBlock)
        
        # Ensure drawings do not block mouse events
        self.rectTop.IsHitTestVisible = False
        self.rectBottom.IsHitTestVisible = False
        self.rectLeft.IsHitTestVisible = False
        self.rectRight.IsHitTestVisible = False
        self.selectionRect.IsHitTestVisible = False
        self.textBlock.IsHitTestVisible = False
        
        self.isDragging = False
        self.startPoint = Point()
        self.finalRect = None
        self.PreviewMouseLeftButtonDown += self.OnMouseDown
        self.PreviewMouseMove += self.OnMouseMove
        self.PreviewMouseLeftButtonUp += self.OnMouseUp
        
        self.PreviewKeyDown += self.OnKeyDown
        self.Loaded += self.OnLoaded
        self.Focusable = True

    def OnLoaded(self, sender, e):
        self.Activate()
        self.Focus()
        self.canvas.Focus()

    def OnMouseDown(self, sender, e):
        self.isDragging = True
        self.startPoint = e.GetPosition(self.canvas)
        self.selectionRect.Visibility = Visibility.Visible
        Canvas.SetLeft(self.selectionRect, self.startPoint.X)
        Canvas.SetTop(self.selectionRect, self.startPoint.Y)
        self.selectionRect.Width = 0
        self.selectionRect.Height = 0
        self.rectTop.Width = self.Width
        self.rectTop.Height = self.Height
        self.rectBottom.Width = self.Width
        self.rectBottom.Height = 0
        self.rectLeft.Width = 0
        self.rectRight.Width = 0
        self.CaptureMouse()

    def OnMouseMove(self, sender, e):
        if self.isDragging:
            pos = e.GetPosition(self.canvas)
            x = min(pos.X, self.startPoint.X)
            y = min(pos.Y, self.startPoint.Y)
            w = abs(pos.X - self.startPoint.X)
            h = abs(pos.Y - self.startPoint.Y)
            
            Canvas.SetLeft(self.selectionRect, x)
            Canvas.SetTop(self.selectionRect, y)
            self.selectionRect.Width = w
            self.selectionRect.Height = h
            
            self.rectTop.Height = y
            
            Canvas.SetTop(self.rectBottom, y + h)
            self.rectBottom.Height = max(0, self.Height - (y + h))
            
            Canvas.SetTop(self.rectLeft, y)
            self.rectLeft.Height = h
            self.rectLeft.Width = x
            
            Canvas.SetTop(self.rectRight, y)
            Canvas.SetLeft(self.rectRight, x + w)
            self.rectRight.Height = h
            self.rectRight.Width = max(0, self.Width - (x + w))

    def OnMouseUp(self, sender, e):
        if self.isDragging:
            self.isDragging = False
            self.ReleaseMouseCapture()
            
            if self.selectionRect.Width > 5 and self.selectionRect.Height > 5:
                x = Canvas.GetLeft(self.selectionRect)
                y = Canvas.GetTop(self.selectionRect)
                w = self.selectionRect.Width
                h = self.selectionRect.Height
                self.finalRect = Rect(x, y, w, h)
                self.DialogResult = True
            else:
                self.DialogResult = False
            
    def OnKeyDown(self, sender, e):
        if e.Key == Key.Escape:
            self.DialogResult = False
            self.Close()

def main():
    try:
        # Verify we are in a valid view
        active_view = doc.ActiveView
        valid_view_types = [
            DB.ViewType.FloorPlan, DB.ViewType.CeilingPlan, DB.ViewType.EngineeringPlan,
            DB.ViewType.Section, DB.ViewType.Elevation, DB.ViewType.DraftingView,
            DB.ViewType.Detail, DB.ViewType.ThreeD
        ]
        
        if active_view.ViewType not in valid_view_types:
            forms.alert("Please open an appropriate view to select a print area.", exitscript=True)

        # Find the current UIView
        uiviews = uidoc.GetOpenUIViews()
        active_uiview = None
        for uv in uiviews:
            if uv.ViewId == active_view.Id:
                active_uiview = uv
                break

        if not active_uiview:
            sys.exit()

        rect = active_uiview.GetWindowRectangle()

        # Get DPI Scale
        g = Drawing.Graphics.FromHwnd(System.IntPtr.Zero)
        scaleX = g.DpiX / 96.0
        scaleY = g.DpiY / 96.0
        g.Dispose()

        # Show custom selection window
        win = SnippingWindow(rect, scaleX, scaleY)
        result = win.ShowDialog()

        if not result or not win.finalRect:
            forms.alert("Selection canceled or area too small.", exitscript=True)

        # Map selected pixel coordinates to physical screen pixels
        px_left = win.finalRect.Left * scaleX
        px_top = win.finalRect.Top * scaleY
        px_width = win.finalRect.Width * scaleX
        px_height = win.finalRect.Height * scaleY

        window_w = float(rect.Right - rect.Left)
        window_h = float(rect.Bottom - rect.Top)

        corners = active_uiview.GetZoomCorners()
        xyz_bl = corners[0]
        xyz_tr = corners[1]

        # In model space
        view_right = active_view.RightDirection
        view_up = active_view.UpDirection

        # Width and Height of the view in model space
        model_w = (xyz_tr - xyz_bl).DotProduct(view_right)
        model_h = (xyz_tr - xyz_bl).DotProduct(view_up)

        # Center of selection in physical pixels
        center_px_x = px_left + px_width / 2.0
        center_px_y = px_top + px_height / 2.0

        # Interpolate to find model coordinates
        fraction_x = center_px_x / window_w
        fraction_y = center_px_y / window_h

        # Model center
        model_center = xyz_bl + view_right.Multiply(fraction_x * model_w) + view_up.Multiply((1.0 - fraction_y) * model_h)

        # Selection width and height in model space
        sel_model_w = (px_width / window_w) * model_w
        sel_model_h = (px_height / window_h) * model_h

        # Calculate new corners
        new_bl = model_center - view_right.Multiply(sel_model_w / 2.0) - view_up.Multiply(sel_model_h / 2.0)
        new_tr = model_center + view_right.Multiply(sel_model_w / 2.0) + view_up.Multiply(sel_model_h / 2.0)

        # Zoom to the selected area
        active_uiview.ZoomAndCenterRectangle(new_bl, new_tr)
        
        # Refresh the view so the Print command captures the new zoomed area
        uidoc.RefreshActiveView()
        
        # Try to set the PrintManager to VisibleRegionOfCurrentView
        try:
            print_manager = doc.PrintManager
            with revit.Transaction("Print Settings"):
                print_manager.PrintRange = DB.PrintRange.Visible
                print_manager.Apply()
        except Exception:
            pass

        # Call the Print dialog
        print_cmd_id = UI.RevitCommandId.LookupPostableCommandId(UI.PostableCommand.Print)
        if print_cmd_id and uidoc.Application.CanPostCommand(print_cmd_id):
            uidoc.Application.PostCommand(print_cmd_id)
        else:
            forms.alert("Unable to open the print dialog automatically.")
            
    except Exception as e:
        import traceback
        forms.alert("Error: {}\n\nTraceback:\n{}".format(e, traceback.format_exc()))

if __name__ == '__main__':
    main()
