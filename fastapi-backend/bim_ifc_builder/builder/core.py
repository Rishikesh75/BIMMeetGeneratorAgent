from pathlib import Path

import ifcopenshell.api

from bim_ifc_builder.builder.elements.registry import create_element
from bim_ifc_builder.builder.hierarchy import create_spatial_hierarchy
from bim_ifc_builder.schemas.building_plan import BuildingPlan


def build_ifc(plan: BuildingPlan, output_path: str | Path) -> Path:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    model = ifcopenshell.api.run("project.create_file", version="IFC4")

    project = ifcopenshell.api.run(
        "root.create_entity",
        model,
        ifc_class="IfcProject",
        name=plan.name,
    )
    ifcopenshell.api.run("unit.assign_unit", model)

    context = _create_body_context(model)
    storeys = create_spatial_hierarchy(model, plan, project)

    for element in plan.elements:
        storey = storeys.get(element.floor)
        if storey is None:
            raise ValueError(f"Floor {element.floor} does not exist in building plan with {plan.floors} floor(s)")
        create_element(model, context, storey, element)

    model.write(str(output_path))
    return output_path


def _create_body_context(model):
    model3d = ifcopenshell.api.run("context.add_context", model, context_type="Model")
    return ifcopenshell.api.run(
        "context.add_context",
        model,
        context_type="Model",
        context_identifier="Body",
        target_view="MODEL_VIEW",
        parent=model3d,
    )
