# -*- coding: utf-8 -*-
"""Copy Scope Boxes from a selected Revit Link into the current document."""

__title__ = "Scope Box\nCopier"
__author__ = "pyTal"

# ───────────────────────────── Imports ──────────────────────────────
import clr
clr.AddReference("RevitAPI")
clr.AddReference("RevitAPIUI")

from Autodesk.Revit.DB import (
    FilteredElementCollector,
    RevitLinkInstance,
    RevitLinkType,
    BuiltInCategory,
    Element,
    ElementId,
    CopyPasteOptions,
    ElementTransformUtils,
    Transform,
    Transaction,
)
from pyrevit import revit, DB, forms, script

# ───────────────────────────── Globals ──────────────────────────────
doc = revit.doc
uidoc = revit.uidoc
output = script.get_output()


# ──────────────────────── Helper Functions ──────────────────────────
def pick_link_instance():
    """Show a menu of all Revit links and let the user pick one."""
    # Collect all link instances in the document
    link_instances = (
        FilteredElementCollector(doc)
        .OfClass(RevitLinkInstance)
        .ToElements()
    )

    # Filter to loaded links only
    loaded_links = [
        li for li in link_instances if li.GetLinkDocument() is not None
    ]

    if not loaded_links:
        forms.alert(
            "No loaded Revit links found in the current document.",
            exitscript=True,
        )

    # Build name → instance mapping (use link type name for display)
    link_map = {}
    for li in loaded_links:
        link_type = doc.GetElement(li.GetTypeId())
        name = Element.Name.GetValue(link_type) if link_type else str(li.Id)
        # Handle multiple instances of the same link type
        if name in link_map:
            name = "{} (Instance {})".format(name, li.Id)
        link_map[name] = li

    # Let user pick from sorted list
    selected_name = forms.SelectFromList.show(
        sorted(link_map.keys()),
        title="Select a Revit Link",
        button_name="Select",
        multiselect=False,
        width=400,
        height=300,
    )

    if not selected_name:
        return None

    return link_map[selected_name]


def get_scope_boxes(document):
    """Return all scope boxes (VolumeOfInterest) in the given document."""
    collector = (
        FilteredElementCollector(document)
        .OfCategory(BuiltInCategory.OST_VolumeOfInterest)
        .WhereElementIsNotElementType()
    )
    return list(collector)


def get_existing_scope_box_names(document):
    """Return a set of scope box names already present in the document."""
    existing = get_scope_boxes(document)
    return {sb.Name for sb in existing}


def copy_scope_boxes(link_instance):
    """Copy scope boxes from the linked document into the current document.

    Uses ElementTransformUtils.CopyElements to bring scope boxes across
    documents, which preserves geometry and parameters.
    """
    link_doc = link_instance.GetLinkDocument()
    if link_doc is None:
        forms.alert(
            "The selected link is not loaded.\n"
            "Please load the link and try again.",
            exitscript=True,
        )

    # Gather scope boxes from the linked document
    link_scope_boxes = get_scope_boxes(link_doc)
    if not link_scope_boxes:
        forms.alert(
            "No scope boxes found in the selected link.",
            exitscript=True,
        )

    # Get existing names to report duplicates
    existing_names = get_existing_scope_box_names(doc)

    # Let user pick which scope boxes to copy
    scope_box_options = sorted(
        [sb.Name for sb in link_scope_boxes]
    )
    selected_names = forms.SelectFromList.show(
        scope_box_options,
        title="Select Scope Boxes to Copy",
        button_name="Copy Selected",
        multiselect=True,
        width=400,
        height=400,
    )

    if not selected_names:
        script.exit()

    # Build list of element ids to copy
    ids_to_copy = [
        sb.Id for sb in link_scope_boxes if sb.Name in selected_names
    ]

    # Identify duplicates
    duplicates = [name for name in selected_names if name in existing_names]
    skipped = []
    if duplicates:
        # Ask user whether to skip duplicates
        skip = forms.alert(
            "The following scope boxes already exist in the current model:\n\n"
            + "\n".join("  • " + d for d in duplicates)
            + "\n\nDo you want to copy them anyway (duplicates will be created)?",
            yes=True,
            no=True,
        )
        if not skip:
            # Remove duplicate ids from copy list
            ids_to_copy = [
                sb.Id
                for sb in link_scope_boxes
                if sb.Name in selected_names and sb.Name not in existing_names
            ]
            skipped = duplicates

    if not ids_to_copy:
        forms.alert("No scope boxes to copy after skipping duplicates.")
        script.exit()

    # Collect .NET List of ElementIds
    from System.Collections.Generic import List
    id_list = List[ElementId](ids_to_copy)

    # Copy elements across documents
    copied_count = 0
    with revit.Transaction("Copy Scope Boxes from Link"):
        try:
            # Apply the link transform so boxes land in the correct position
            link_transform = link_instance.GetTotalTransform()
            options = CopyPasteOptions()

            new_ids = ElementTransformUtils.CopyElements(
                link_doc,          # source document
                id_list,           # element ids to copy
                doc,               # destination document
                link_transform,    # transform to apply
                options,           # copy-paste options
            )
            copied_count = len(list(new_ids))
        except Exception as ex:
            forms.alert(
                "Error while copying scope boxes:\n{}".format(str(ex)),
                exitscript=True,
            )

    # Report results
    summary_lines = []
    summary_lines.append(
        "✅ Successfully copied {} scope box(es).".format(copied_count)
    )
    if skipped:
        summary_lines.append(
            "⏭️ Skipped {} duplicate(s): {}".format(
                len(skipped), ", ".join(skipped)
            )
        )
    forms.alert("\n".join(summary_lines))


# ──────────────────────────── Main ──────────────────────────────────
if __name__ == "__main__":
    link = pick_link_instance()
    if link:
        copy_scope_boxes(link)
