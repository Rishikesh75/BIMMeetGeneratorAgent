import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi import HTTPException

from app.routers.ifc import generate_ifc
from app.routers.plan import generate_plan
from app.schemas.models import TextToIfcRequest
from app.services.bim_llm import EXPECTED_KEYS, GenerationResult, ModelNotReadyError


def _request() -> TextToIfcRequest:
    return TextToIfcRequest(description="Create a one-storey office wall")


def _hierarchical_plan() -> dict:
    plan = {key: [] for key in EXPECTED_KEYS}
    plan["project"] = {"name": "Office"}
    plan["storeys"] = [{"id": "storey-001", "name": "Ground"}]
    plan["elements"] = {
        "walls": [
            {
                "name": "North Wall",
                "storey": "storey-001",
                "geometry": {
                    "start": [0, 0, 0],
                    "end": [5, 0, 0],
                    "height": 3,
                    "thickness": 0.2,
                },
            }
        ],
        "slabs": [],
    }
    return plan


class GenerateRouteTests(unittest.TestCase):
    def test_plan_generate_returns_invalid_json_text(self):
        result = GenerationResult(
            raw_text="not json",
            valid_json=False,
            valid_structure=False,
            plan=None,
        )
        with patch("app.routers.plan.bim_llm.generate", return_value=result):
            response = generate_plan(_request())

        self.assertFalse(response["valid_json"])
        self.assertFalse(response["valid_structure"])
        self.assertIsNone(response["plan"])
        self.assertEqual(response["raw_text"], "not json")

    def test_plan_generate_returns_structure_flags(self):
        payload = _hierarchical_plan()
        result = GenerationResult(
            raw_text="{}",
            valid_json=True,
            valid_structure=True,
            plan=payload,
        )
        with patch("app.routers.plan.bim_llm.generate", return_value=result):
            response = generate_plan(_request())

        self.assertTrue(response["valid_json"])
        self.assertTrue(response["valid_structure"])
        self.assertEqual(response["plan"]["project"]["name"], "Office")

    def test_ifc_generate_maps_model_json(self):
        result = GenerationResult(
            raw_text="{}",
            valid_json=True,
            valid_structure=True,
            plan=_hierarchical_plan(),
        )
        with (
            patch("app.routers.ifc.bim_llm.generate", return_value=result),
            patch("app.routers.ifc.save_ifc_from_plan", return_value=Path("generated_model.ifc")) as save,
        ):
            response = generate_ifc(_request())

        saved_plan = save.call_args.args[0]
        self.assertEqual(saved_plan.elements[0].type, "wall")
        self.assertEqual(response["file_name"], "generated_model.ifc")

    def test_ifc_generate_rejects_unmappable_json(self):
        payload = _hierarchical_plan()
        payload["elements"] = {"walls": [], "slabs": []}
        result = GenerationResult(
            raw_text="{}",
            valid_json=True,
            valid_structure=True,
            plan=payload,
        )
        with patch("app.routers.ifc.bim_llm.generate", return_value=result):
            with self.assertRaises(HTTPException) as caught:
                generate_ifc(_request())

        self.assertEqual(caught.exception.status_code, 422)
        self.assertIn("no mappable walls", caught.exception.detail["message"])

    def test_model_not_ready_is_503(self):
        with patch(
            "app.routers.ifc.bim_llm.generate",
            side_effect=ModelNotReadyError("adapter missing"),
        ):
            with self.assertRaises(HTTPException) as caught:
                generate_ifc(_request())

        self.assertEqual(caught.exception.status_code, 503)


if __name__ == "__main__":
    unittest.main()
