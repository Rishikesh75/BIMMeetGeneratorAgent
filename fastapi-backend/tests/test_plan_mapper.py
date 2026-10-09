import math
import tempfile
import unittest
from pathlib import Path

import ifcopenshell

from app.services.plan_mapper import PlanMappingError, hierarchical_to_building_plan
from bim_ifc_builder import build_ifc


def _plan(**overrides):
    plan = {
        "project": {"id": "proj-001", "name": "North Wing Study"},
        "site": {"id": "site-001", "name": "Main Campus"},
        "building": {"id": "bld-001", "name": "North Wing", "storeys": ["storey-001"]},
        "storeys": [{"id": "storey-001", "name": "Ground Floor", "elevation": 0.0, "height": 3.0}],
        "elements": {
            "walls": [
                {
                    "id": "wall-001",
                    "name": "Exterior Wall North",
                    "storey": "storey-001",
                    "geometry": {
                        "start": [0.0, 0.0, 0.0],
                        "end": [5.0, 0.0, 0.0],
                        "height": 3.0,
                        "thickness": 0.2,
                    },
                }
            ],
            "slabs": [],
        },
    }
    plan.update(overrides)
    return plan


class PlanMapperTests(unittest.TestCase):
    def test_wall_becomes_length_and_rotation(self):
        plan = hierarchical_to_building_plan(
            _plan(
                elements={
                    "walls": [
                        {
                            "id": "wall-001",
                            "name": "Diagonal",
                            "storey": "storey-001",
                            "geometry": {
                                "start": [1.0, 2.0, 0.5],
                                "end": [4.0, 6.0, 0.5],
                                "height": 3.0,
                                "thickness": 0.2,
                            },
                        }
                    ],
                    "slabs": [],
                }
            ),
            fallback_name="unused",
        )

        wall = plan.elements[0]
        self.assertEqual(plan.name, "North Wing Study")
        self.assertEqual(plan.floors, 1)
        self.assertEqual(wall.type, "wall")
        self.assertAlmostEqual(wall.length_m, 5.0)
        self.assertAlmostEqual(wall.rotation_deg, math.degrees(math.atan2(4.0, 3.0)))
        self.assertEqual(wall.position.x, 1.0)
        self.assertEqual(wall.position.y, 2.0)
        self.assertEqual(wall.position.z, 0.5)
        self.assertEqual(wall.height_m, 3.0)
        self.assertEqual(wall.thickness_m, 0.2)

    def test_second_storey_wall_and_slab_bbox(self):
        plan = hierarchical_to_building_plan(
            _plan(
                storeys=[
                    {"id": "storey-001", "name": "Ground Floor"},
                    {"id": "storey-002", "name": "First Floor"},
                ],
                elements={
                    "walls": [
                        {
                            "name": "Upper Wall",
                            "storey": "storey-002",
                            "geometry": {
                                "start": [0, 0, 3],
                                "end": [0, 4, 3],
                                "height": 3,
                                "thickness": 0.2,
                            },
                        }
                    ],
                    "slabs": [
                        {
                            "name": "Floor Slab",
                            "storey": "storey-001",
                            "thickness": 0.25,
                            "outline": [[1, 2, 0], [6, 2, 0], [6, 8, 0], [1, 8, 0]],
                        }
                    ],
                },
            ),
            fallback_name="unused",
        )

        self.assertEqual(plan.floors, 2)
        wall = next(element for element in plan.elements if element.type == "wall")
        slab = next(element for element in plan.elements if element.type == "slab")
        self.assertEqual(wall.floor, 2)
        self.assertAlmostEqual(wall.length_m, 4.0)
        self.assertAlmostEqual(wall.rotation_deg, 90.0)
        self.assertEqual(slab.floor, 1)
        self.assertAlmostEqual(slab.width_m, 5.0)
        self.assertAlmostEqual(slab.depth_m, 6.0)
        self.assertEqual(slab.thickness_m, 0.25)
        self.assertEqual((slab.position.x, slab.position.y, slab.position.z), (1.0, 2.0, 0.0))

    def test_mapped_wall_builds_ifc(self):
        plan = hierarchical_to_building_plan(_plan(), fallback_name="Office")

        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = build_ifc(plan, Path(temp_dir) / "mapped.ifc")
            model = ifcopenshell.open(str(output_path))
            self.assertEqual(len(model.by_type("IfcWall")), 1)

    def test_empty_elements_raise(self):
        with self.assertRaises(PlanMappingError):
            hierarchical_to_building_plan(
                _plan(elements={"walls": [], "slabs": [], "columns": [{"id": "col-001"}]}),
                fallback_name="Office",
            )

    def test_missing_elements_object_raises(self):
        payload = _plan()
        del payload["elements"]
        with self.assertRaises(PlanMappingError):
            hierarchical_to_building_plan(payload, fallback_name="Office")

    def test_fallback_name_when_project_name_missing(self):
        plan = hierarchical_to_building_plan(
            _plan(project={"id": "proj-001", "name": "  "}, building={"name": ""}),
            fallback_name="A long office description",
        )
        self.assertEqual(plan.name, "A long office description")


if __name__ == "__main__":
    unittest.main()
