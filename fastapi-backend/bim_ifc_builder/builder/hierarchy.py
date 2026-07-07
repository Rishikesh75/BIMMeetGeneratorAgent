import ifcopenshell.api

from bim_ifc_builder.schemas.building_plan import BuildingPlan


def create_spatial_hierarchy(model, plan: BuildingPlan, project) -> dict[int, object]:
    site = ifcopenshell.api.run(
        "root.create_entity",
        model,
        ifc_class="IfcSite",
        name="Site",
    )
    building = ifcopenshell.api.run(
        "root.create_entity",
        model,
        ifc_class="IfcBuilding",
        name=plan.name,
    )

    storeys: dict[int, object] = {}
    for floor in range(1, plan.floors + 1):
        storeys[floor] = ifcopenshell.api.run(
            "root.create_entity",
            model,
            ifc_class="IfcBuildingStorey",
            name=f"Level {floor}",
        )

    ifcopenshell.api.run("aggregate.assign_object", model, relating_object=project, products=[site])
    ifcopenshell.api.run("aggregate.assign_object", model, relating_object=site, products=[building])
    ifcopenshell.api.run(
        "aggregate.assign_object",
        model,
        relating_object=building,
        products=list(storeys.values()),
    )

    return storeys
