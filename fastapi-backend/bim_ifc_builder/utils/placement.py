import math

import numpy as np

from bim_ifc_builder.schemas.building_plan import BuildingElement


def build_placement_matrix(element: BuildingElement) -> np.ndarray:
    matrix = np.eye(4)
    angle = math.radians(element.rotation_deg)
    cos_a = math.cos(angle)
    sin_a = math.sin(angle)

    matrix[0, 0] = cos_a
    matrix[0, 1] = -sin_a
    matrix[1, 0] = sin_a
    matrix[1, 1] = cos_a
    matrix[0:3, 3] = [element.position.x, element.position.y, element.position.z]
    return matrix
