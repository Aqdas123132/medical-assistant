"""
utils.py - Helper functions: safe JSON parsing, input cleaning, safety rules.

The most important rule of this file: bad JSON from the model must NEVER
crash the app. Every function here fails politely instead of raising errors.
"""

import json
import re

from src.config import (
    EMERGENCY_COMBINATIONS,
    RED_FLAG_SYMPTOMS,
    URGENCY_LEVELS,
)

# The keys every result must have (taken from the assignment schema).
EXPECTED_KEYS = [
    "summary",
    "possible_conditions",
    "urgency_level",
    "recommended_next_steps",
    "questions_for_doctor",
    "warning_signs",
]


# --------------------------------------------------------------------------
# JSON parsing
# --------------------------------------------------------------------------
def strip_code_fences(text: str) -> str:
    """Remove accidental ```json ... ``` fences around the model output."""
    text = text.strip()
    # Remove an opening fence like ``` or ```json
    text = re.sub(r"^```(?:json|JSON)?\s*", "", text)
    # Remove a closing fence
    text = re.sub(r"\s*```$", "", text)
    return text.strip()


def extract_json_object(text: str) -> str:
    """If there is extra text around the JSON, keep only the { ... } part."""
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        return text[start : end + 1]
    return text


def safe_parse_json(raw_text: str):
    """
    Try to turn the model output into a Python dict.

    Returns a tuple: (data, error_message)
      - on success: (dict, None)
      - on failure: (None, "friendly error text")
    """
    if not raw_text or not raw_text.strip():
        return None, "The model returned an empty answer."

    cleaned = extract_json_object(strip_code_fences(raw_text))
    try:
        data = json.loads(cleaned)
    except (json.JSONDecodeError, TypeError) as err:
        return None, f"The model's answer was not valid JSON ({err})."

    if not isinstance(data, dict):
        return None, "The model's answer was JSON, but not a JSON object."

    return data, None


# --------------------------------------------------------------------------
# Result cleaning
# --------------------------------------------------------------------------
def _to_list_of_strings(value) -> list:
    """Make sure a value is a list of non-empty strings."""
    if isinstance(value, str):
        value = [value]
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def normalize_result(data: dict) -> dict:
    """
    Fill in missing keys and fix wrong types so the UI can always render.
    The model sometimes returns slightly different shapes; we tolerate that.
    """
    result = {}
    result["summary"] = str(data.get("summary", "")).strip()

    # possible_conditions should be a list of {"name":..., "reason":...}
    conditions = []
    raw_conditions = data.get("possible_conditions", [])
    if isinstance(raw_conditions, list):
        for item in raw_conditions:
            if isinstance(item, dict):
                name = str(item.get("name", "")).strip()
                reason = str(item.get("reason", "")).strip()
                if name:
                    conditions.append({"name": name, "reason": reason})
            elif str(item).strip():
                conditions.append({"name": str(item).strip(), "reason": ""})
    result["possible_conditions"] = conditions

    # Urgency must be one of the four allowed values.
    urgency = str(data.get("urgency_level", "")).strip().upper()
    result["urgency_level"] = urgency if urgency in URGENCY_LEVELS else "MEDIUM"

    result["recommended_next_steps"] = _to_list_of_strings(
        data.get("recommended_next_steps", [])
    )
    result["questions_for_doctor"] = _to_list_of_strings(
        data.get("questions_for_doctor", [])
    )
    result["warning_signs"] = _to_list_of_strings(data.get("warning_signs", []))
    return result


# --------------------------------------------------------------------------
# Safety floor: a rule-based safety net that does not depend on the LLM
# --------------------------------------------------------------------------
def apply_safety_floor(urgency: str, symptoms: list):
    """
    Make sure urgency is never too low for dangerous symptoms.

    Returns (new_urgency, note). `note` is a short text if we raised the
    urgency, otherwise None.
    """
    symptom_text = " ".join(symptoms).lower()
    floor = "LOW"

    if any(flag in symptom_text for flag in RED_FLAG_SYMPTOMS):
        floor = "HIGH"
    for combo in EMERGENCY_COMBINATIONS:
        if all(part in symptom_text for part in combo):
            floor = "EMERGENCY"

    if URGENCY_LEVELS.index(urgency) < URGENCY_LEVELS.index(floor):
        note = (
            f"Safety rule: urgency was raised from {urgency} to {floor} "
            "because of the symptoms you reported."
        )
        return floor, note
    return urgency, None


# --------------------------------------------------------------------------
# Input helpers
# --------------------------------------------------------------------------
def build_symptom_list(selected: list, free_text: str) -> list:
    """Combine multiselect choices and comma-separated free text."""
    symptoms = list(selected)
    for part in re.split(r"[,\n;]", free_text or ""):
        part = part.strip()
        if part and part.lower() not in [s.lower() for s in symptoms]:
            symptoms.append(part)
    return symptoms


def validate_age(age_text: str):
    """Return (age_as_int, error_message). Exactly one of them is None."""
    age_text = (age_text or "").strip()
    if not age_text:
        return None, "Please enter the patient's age."
    if not age_text.isdigit():
        return None, "Age must be a whole number (for example 25)."
    age = int(age_text)
    if age < 0 or age > 120:
        return None, "Age must be between 0 and 120."
    return age, None


def build_chain_inputs(
    age, gender, symptoms, duration, severity, conditions, medications, notes, language
) -> dict:
    """Build the dictionary of variables that the prompt templates expect."""
    return {
        "age": age,
        "gender": gender,
        "symptoms": ", ".join(symptoms),
        "duration": duration,
        "severity": severity,
        "conditions": (conditions or "").strip() or "None reported",
        "medications": (medications or "").strip() or "None reported",
        "notes": (notes or "").strip() or "None",
        "language": language,
    }
def assessment_to_inputs(a: dict) -> dict:
    """
    Turn a saved assessment (from the database) back into the dictionary of
    prompt inputs, so the follow-up chat knows the patient's details.
    """
    keys = [
        "age", "gender", "symptoms", "duration", "severity",
        "conditions", "medications", "notes", "language",
    ]
    inputs = {}
    for key in keys:
        value = a.get(key)
        inputs[key] = value if value not in (None, "") else "Not provided"
    inputs["language"] = a.get("language") or "English"
    return inputs