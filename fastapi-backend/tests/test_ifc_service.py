import tempfile
import unittest
from pathlib import Path

import ifcopenshell

from app.services.ifc_service import save_ifc_file, save_ifc_from_plan
from app.services.text_to_plan import text_to_building_plan
from bim_ifc_builder import BuildingElement, BuildingPlan, build_ifc
from bim_ifc_builder.exceptions import UnsupportedElementTypeError


class TextToPlanTests(unittest.TestCase):
    def test_text_to_building_plan_creates_default_elements(self):
        plan = text_to_building_plan("Warehouse building with steel beams")

        self.assertEqual(plan.building_type, "warehouse")
        self.assertGreaterEqual(len(plan.elements), 5)
        self.assertTrue(any(element.type == "wall" for element in plan.elements))
        self.assertTrue(any(element.type == "slab" for element in plan.elements))


class IFCBuilderTests(unittest.TestCase):
    def test_build_ifc_creates_wall_and_slab(self):
        plan = BuildingPlan(
            name="Test Office",
            floors=1,
            elements=[
                BuildingElement(
                    type="wall",
                    name="Wall 1",
                    length_m=10,
                    height_m=3,
                    thickness_m=0.2,
                ),
                BuildingElement(
                    type="slab",
                    name="Floor",
                    width_m=8,
                    depth_m=6,
                    thickness_m=0.25,
                ),
            ],
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = build_ifc(plan, Path(temp_dir) / "test.ifc")
            model = ifcopenshell.open(str(output_path))

            self.assertEqual(len(model.by_type("IfcWall")), 1)
            self.assertEqual(len(model.by_type("IfcSlab")), 1)
            self.assertEqual(len(model.by_type("IfcBuildingStorey")), 1)

    def test_unsupported_element_type_raises(self):
        plan = BuildingPlan(
            name="Invalid Plan",
            elements=[
                BuildingElement(type="door", name="Front Door", width_m=1.0, height_m=2.1),
            ],
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            with self.assertRaises(UnsupportedElementTypeError):
                build_ifc(plan, Path(temp_dir) / "invalid.ifc")


class IFCServiceTests(unittest.TestCase):
    def test_save_ifc_from_plan_writes_file(self):
        plan = BuildingPlan(
            name="Service Test",
            elements=[
                BuildingElement(type="wall", name="W1", length_m=5, height_m=3, thickness_m=0.2),
            ],
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = save_ifc_from_plan(plan, output_dir=temp_dir)
            self.assertTrue(output_path.exists())
            self.assertEqual(output_path.name, "generated_model.ifc")

    def test_save_ifc_file_from_text_writes_valid_ifc(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = save_ifc_file("Office building 12m wide", output_dir=temp_dir)
            model = ifcopenshell.open(str(output_path))

            self.assertTrue(output_path.exists())
            self.assertGreaterEqual(len(model.by_type("IfcWall")), 1)


if __name__ == "__main__":
    unittest.main()
