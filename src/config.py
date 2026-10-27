"""
config.py - Settings and form options for MediGuide AI.

Everything that is a "setting" (API key, model names, dropdown choices,
disclaimer text, colours) lives here so the rest of the code stays clean.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

# Load variables from the .env file into the environment.
# The API key is NEVER written in the code - it only comes from .env.
load_dotenv()

# --------------------------------------------------------------------------
# Secrets and model settings
# --------------------------------------------------------------------------
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
DEFAULT_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
MODEL_OPTIONS = ["gpt-4o-mini", "gpt-4o", "gpt-4.1-mini"]
DEFAULT_TEMPERATURE = 0.2

# --------------------------------------------------------------------------
# Cache settings
# --------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent
SQLITE_DB_PATH = str(PROJECT_ROOT / "mediguide_cache.db")
CACHE_MODES = ["Off", "In-memory", "SQLite"]

# --------------------------------------------------------------------------
# Form options
# --------------------------------------------------------------------------
GENDER_OPTIONS = ["Male", "Female", "Other", "Prefer not to say"]

SYMPTOM_OPTIONS = [
    "Fever",
    "Cough",
    "Runny nose",
    "Sore throat",
    "Headache",
    "Fatigue",
    "Muscle aches",
    "Nausea",
    "Vomiting",
    "Diarrhea",
    "Abdominal pain",
    "Chest pain",
    "Shortness of breath",
    "Dizziness",
    "Rash",
    "Joint pain",
    "Back pain",
    "Loss of taste or smell",
]

DURATION_OPTIONS = [
    "Less than 24 hours",
    "1-3 days",
    "4-7 days",
    "1-2 weeks",
    "More than 2 weeks",
]

LANGUAGE_OPTIONS = ["English", "Urdu", "Hindi", "Arabic", "Spanish", "French"]

# --------------------------------------------------------------------------
# Urgency levels
# --------------------------------------------------------------------------
# Order matters: index 0 is the least urgent, index 3 is the most urgent.
URGENCY_LEVELS = ["LOW", "MEDIUM", "HIGH", "EMERGENCY"]

URGENCY_COLORS = {
    "LOW": "#2e7d32",        # green
    "MEDIUM": "#f9a825",     # yellow
    "HIGH": "#ef6c00",       # orange
    "EMERGENCY": "#c62828",  # red
}

URGENCY_MESSAGES = {
    "LOW": "Low urgency: symptoms look mild. Monitor them and rest.",
    "MEDIUM": "Medium urgency: consider booking a visit with a healthcare professional soon.",
    "HIGH": "High urgency: please contact a healthcare professional as soon as possible.",
    "EMERGENCY": (
        "EMERGENCY: seek emergency medical help IMMEDIATELY. "
        "Call your local emergency number or go to the nearest emergency department."
    ),
}

# --------------------------------------------------------------------------
# Safety rules used by the app (separate from the LLM's own judgement)
# --------------------------------------------------------------------------
# If any of these symptoms is selected, urgency is never lower than HIGH.
RED_FLAG_SYMPTOMS = [
    "chest pain",
    "shortness of breath",
    "difficulty breathing",
    "severe bleeding",
    "loss of consciousness",
    "fainting",
    "seizure",
    "confusion",
]

# If ALL symptoms in a group are present together, urgency becomes EMERGENCY.
EMERGENCY_COMBINATIONS = [
    ["chest pain", "shortness of breath"],
]

# --------------------------------------------------------------------------
# Disclaimer shown in the sidebar, main area and results
# --------------------------------------------------------------------------
DISCLAIMER_SHORT = (
    "MediGuide AI is an educational AI prototype. It is NOT a doctor, NOT a "
    "diagnosis, and NOT an emergency service. Always consult a qualified "
    "healthcare professional. In an emergency, call your local emergency number."
)

DISCLAIMER_LONG = (
    "**Medical disclaimer:** This tool gives general, educational information "
    "only. It never provides a confirmed diagnosis and must not be used for "
    "real diagnosis or treatment. Please consult a licensed healthcare "
    "professional about your symptoms. If you think you are having an "
    "emergency, seek emergency help immediately."
)
