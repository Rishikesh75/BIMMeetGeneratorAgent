import json
import unittest

from app.services.bim_llm import EXPECTED_KEYS, parse_model_output


class ParseModelOutputTests(unittest.TestCase):
    def test_invalid_text_is_not_json(self):
        result = parse_model_output("this is not json")

        self.assertFalse(result.valid_json)
        self.assertFalse(result.valid_structure)
        self.assertIsNone(result.plan)
        self.assertEqual(result.raw_text, "this is not json")

    def test_partial_object_is_json_without_structure(self):
        result = parse_model_output('{"project": {"name": "Office"}}')

        self.assertTrue(result.valid_json)
        self.assertFalse(result.valid_structure)
        self.assertEqual(result.plan["project"]["name"], "Office")

    def test_expected_keys_mark_valid_structure(self):
        payload = {key: {} for key in EXPECTED_KEYS}
        result = parse_model_output("Here is the model:\n" + json.dumps(payload) + "\nThanks.")

        self.assertTrue(result.valid_json)
        self.assertTrue(result.valid_structure)
        self.assertEqual(set(result.plan), EXPECTED_KEYS)

    def test_markdown_fence_is_parsed(self):
        result = parse_model_output('```json\n{"project": {"name": "Wing"}}\n```')

        self.assertTrue(result.valid_json)
        self.assertEqual(result.plan["project"]["name"], "Wing")


if __name__ == "__main__":
    unittest.main()
