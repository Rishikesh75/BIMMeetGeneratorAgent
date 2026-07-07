from bim_ifc_builder.builder.elements.slab import create_slab
from bim_ifc_builder.builder.elements.wall import create_wall
from bim_ifc_builder.exceptions import UnsupportedElementTypeError
from bim_ifc_builder.schemas.building_plan import BuildingElement

ELEMENT_CREATORS = {
    "wall": create_wall,
    "slab": create_slab,
}


def create_element(model, context, storey, element: BuildingElement) -> None:
    creator = ELEMENT_CREATORS.get(element.type)
    if creator is None:
        raise UnsupportedElementTypeError(f"Unsupported element type: {element.type}")
    creator(model, context, storey, element)
