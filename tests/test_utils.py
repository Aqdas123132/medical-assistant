"""
Simple tests for the helper functions (no API key or internet needed).

Run from the project folder with:
    python -m unittest discover -s tests -v
"""

import os
import sys
import unittest

# Make "src" importable when running the tests from the project root.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.utils import (  # noqa: E402
    apply_safety_floor,
    build_symptom_list,
    normalize_result,
    safe_parse_json,
    validate_age,
)

GOOD_JSON = (
    '{"summary": "ok", "possible_conditions": [{"name": "Common cold", "reason": "mild"}],'
    ' "urgency_level": "low", "recommended_next_steps": ["Rest"],'
    ' "questions_for_doctor": ["Q?"], "warning_signs": ["Fever > 3 days"]}'
)


class JsonParsingTests(unittest.TestCase):
    def test_valid_json(self):
        data, err = safe_parse_json(GOOD_JSON)
        self.assertIsNone(err)
        self.assertEqual(data["summary"], "ok")

    def test_json_with_code_fences(self):
        data, err = safe_parse_json("```json\n" + GOOD_JSON + "\n```")
        self.assertIsNone(err)
        self.assertIsNotNone(data)

    def test_json_with_surrounding_text(self):
        data, err = safe_parse_json("Here you go: " + GOOD_JSON + " Hope it helps!")
        self.assertIsNone(err)
        self.assertIsNotNone(data)

    def test_invalid_json_does_not_crash(self):
        data, err = safe_parse_json("this is not json at all")
        self.assertIsNone(data)
        self.assertTrue(err)

    def test_empty_output(self):
        data, err = safe_parse_json("")
        self.assertIsNone(data)
        self.assertTrue(err)


class NormalizeTests(unittest.TestCase):
    def test_missing_keys_are_filled(self):
        result = normalize_result({})
        self.assertEqual(result["urgency_level"], "MEDIUM")
        self.assertEqual(result["possible_conditions"], [])

    def test_urgency_is_uppercased(self):
        result = normalize_result({"urgency_level": "low"})
        self.assertEqual(result["urgency_level"], "LOW")

    def test_string_conditions_are_accepted(self):
        result = normalize_result({"possible_conditions": ["Cold"]})
        self.assertEqual(result["possible_conditions"][0]["name"], "Cold")


class SafetyFloorTests(unittest.TestCase):
    def test_chest_pain_and_breathlessness_is_emergency(self):
        urgency, note = apply_safety_floor("LOW", ["Chest pain", "Shortness of breath"])
        self.assertEqual(urgency, "EMERGENCY")
        self.assertIsNotNone(note)

    def test_single_red_flag_is_at_least_high(self):
        urgency, _ = apply_safety_floor("LOW", ["Chest pain"])
        self.assertEqual(urgency, "HIGH")

    def test_mild_symptoms_unchanged(self):
        urgency, note = apply_safety_floor("LOW", ["Runny nose", "Sore throat"])
        self.assertEqual(urgency, "LOW")
        self.assertIsNone(note)


class InputTests(unittest.TestCase):
    def test_symptom_list_merges_free_text(self):
        result = build_symptom_list(["Fever"], "ear pain, fever")
        self.assertEqual(result, ["Fever", "ear pain"])

    def test_empty_symptoms(self):
        self.assertEqual(build_symptom_list([], "  "), [])

    def test_age_validation(self):
        self.assertEqual(validate_age("25")[0], 25)
        self.assertIsNotNone(validate_age("")[1])
        self.assertIsNotNone(validate_age("abc")[1])
        self.assertIsNotNone(validate_age("200")[1])


if __name__ == "__main__":
    unittest.main()
