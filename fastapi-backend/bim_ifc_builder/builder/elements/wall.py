import ifcopenshell.api

from bim_ifc_builder.schemas.building_plan import BuildingElement
from bim_ifc_builder.utils.placement import build_placement_matrix


def create_wall(model, context, storey, element: BuildingElement) -> None:
    length = element.length_m or 5.0
    height = element.height_m or 3.0
    thickness = element.thickness_m or 0.2

    wall = ifcopenshell.api.run(
        "root.create_entity",
        model,
        ifc_class="IfcWall",
        name=element.name,
    )

    representation = ifcopenshell.api.run(
        "geometry.add_wall_representation",
        model,
        context=context,
        length=length,
        height=height,
        thickness=thickness,
    )

    ifcopenshell.api.run("geometry.assign_representation", model, product=wall, representation=representation)
    ifcopenshell.api.run(
        "geometry.edit_object_placement",
        model,
        product=wall,
        matrix=build_placement_matrix(element),
    )
    ifcopenshell.api.run("spatial.assign_container", model, relating_structure=storey, products=[wall])
