import ifcopenshell.api

from bim_ifc_builder.schemas.building_plan import BuildingElement
from bim_ifc_builder.utils.placement import build_placement_matrix


def create_slab(model, context, storey, element: BuildingElement) -> None:
    width = element.width_m or 5.0
    depth = element.depth_m or 5.0
    thickness = element.thickness_m or 0.25

    slab = ifcopenshell.api.run(
        "root.create_entity",
        model,
        ifc_class="IfcSlab",
        name=element.name,
        predefined_type="FLOOR",
    )

    polyline = [
        (0.0, 0.0),
        (width, 0.0),
        (width, depth),
        (0.0, depth),
        (0.0, 0.0),
    ]

    representation = ifcopenshell.api.run(
        "geometry.add_slab_representation",
        model,
        context=context,
        depth=thickness,
        polyline=polyline,
    )

    ifcopenshell.api.run("geometry.assign_representation", model, product=slab, representation=representation)
    ifcopenshell.api.run(
        "geometry.edit_object_placement",
        model,
        product=slab,
        matrix=build_placement_matrix(element),
    )
    ifcopenshell.api.run("spatial.assign_container", model, relating_structure=storey, products=[slab])
