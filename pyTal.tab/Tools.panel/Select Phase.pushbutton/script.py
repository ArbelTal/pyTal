from pyrevit import revit, forms
from Autodesk.Revit.DB import FilteredElementCollector, Phase, BuiltInParameter, BuiltInCategory, CategoryType, ElementId
from System.Collections.Generic import List
import System

# Initialize document
uidoc = __revit__.ActiveUIDocument
doc = uidoc.Document

# Get all phases in the model
phases = FilteredElementCollector(doc).OfClass(Phase).ToElements()
phase_names = [phase.Name for phase in phases]

# Prompt user to select a single phase
selected_phase_name = forms.SelectFromList.show(
    phase_names,
    title="Select a Phase",
    multiselect=False  # Ensure only one selection is allowed
)

# Check if a phase was selected
if selected_phase_name:
    # Find the selected phase object
    selected_phase = next((phase for phase in phases if phase.Name == selected_phase_name), None)

    if selected_phase:
        # Retrieve all model categories in the document
        all_categories = doc.Settings.Categories
        model_categories = [cat for cat in all_categories if cat.CategoryType == CategoryType.Model]
        category_names = [cat.Name for cat in model_categories]

        # Prompt user to select one or more categories
        selected_category_names = forms.SelectFromList.show(
            category_names,
            title="Select Categories",
            multiselect=True  # Allow multiple selections
        )

        # Check if categories were selected
        if selected_category_names:
            # Map selected category names to Category objects
            selected_categories = [
                cat for cat in model_categories if cat.Name in selected_category_names
            ]

            # Collect all family instances in the selected categories
            with revit.Transaction("Select Families by Phase and Category"):
                phase_family_instances = []
                for category in selected_categories:
                    try:
                        # Convert the category Id to BuiltInCategory
                        bic = System.Enum.ToObject(BuiltInCategory, category.Id.IntegerValue)

                        # Collect elements in the current category
                        family_instances = FilteredElementCollector(doc) \
                            .OfCategory(bic) \
                            .WhereElementIsNotElementType() \
                            .ToElements()

                        # Filter instances by the selected phase
                        phase_family_instances.extend([
                            instance for instance in family_instances
                            if instance.get_Parameter(BuiltInParameter.PHASE_CREATED) and
                               instance.get_Parameter(BuiltInParameter.PHASE_CREATED).AsElementId() == selected_phase.Id
                        ])
                    except Exception as e:
                        # Print debug message for categories that cannot be processed
                        print("Could not process category {0}. Error: {1}".format(category.Name, e))

                # Select the filtered family instances in the Revit UI
                if phase_family_instances:
                    element_ids = [family.Id for family in phase_family_instances]
                    uidoc.Selection.SetElementIds(List[ElementId](element_ids))
                else:
                    print("No family instances found for the selected phase and categories.")
