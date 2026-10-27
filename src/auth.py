"""
auth.py - Sign up, log in, log out.

Security ideas used here (all beginner friendly):
  * Passwords are never stored. We store a salted PBKDF2 hash instead.
  * Wrong passwords are counted; after MAX_FAILED_ATTEMPTS the account is
    locked for LOCK_MINUTES.
  * Every signup / login / failed / locked / logout is written to login_events
    so the admin can see the records.
"""

import hashlib
import hmac
import re
import secrets
from datetime import datetime

from src import database

MAX_FAILED_ATTEMPTS = 5
LOCK_MINUTES = 5
PBKDF2_ROUNDS = 200_000

USERNAME_RE = re.compile(r"^[A-Za-z0-9_]{3,30}$")
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


# --------------------------------------------------------------------------
# Password hashing
# --------------------------------------------------------------------------
def hash_password(password: str) -> str:
    """Return 'salt$hash' (both in hex). A new random salt is used each time."""
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PBKDF2_ROUNDS)
    return f"{salt.hex()}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        salt_hex, hash_hex = stored.split("$", 1)
        salt = bytes.fromhex(salt_hex)
        expected = bytes.fromhex(hash_hex)
    except ValueError:
        return False
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PBKDF2_ROUNDS)
    return hmac.compare_digest(digest, expected)  # constant-time comparison


# --------------------------------------------------------------------------
# Validation
# --------------------------------------------------------------------------
def validate_registration(username, full_name, email, password, confirm) -> list:
    """Return a list of friendly error messages (empty list = everything is fine)."""
    errors = []
    username = (username or "").strip()
    if not (full_name or "").strip():
        errors.append("Please enter your full name.")
    if not USERNAME_RE.match(username):
        errors.append("Username must be 3-30 characters: letters, numbers or underscore.")
    elif database.get_user_by_username(username):
        errors.append("That username is already taken. Please choose another.")
    if not EMAIL_RE.match((email or "").strip()):
        errors.append("Please enter a valid email address.")
    password = password or ""
    if len(password) < 8 or not re.search(r"[A-Za-z]", password) or not re.search(r"\d", password):
        errors.append("Password must be at least 8 characters with a letter and a number.")
    if password != (confirm or ""):
        errors.append("The two passwords do not match.")
    return errors


def _public_user(row: dict) -> dict:
    """The user info we keep in st.session_state (never includes the hash)."""
    return {
        "id": row["id"],
        "username": row["username"],
        "full_name": row["full_name"],
        "email": row["email"],
        "role": row["role"],
    }


# --------------------------------------------------------------------------
# Register / login / logout
# --------------------------------------------------------------------------
def register(username, full_name, email, password, confirm):
    """Returns (user, errors). On success errors is an empty list."""
    errors = validate_registration(username, full_name, email, password, confirm)
    if errors:
        return None, errors

    username = username.strip()
    user_id = database.create_user(
        username, full_name.strip(), email.strip(), hash_password(password)
    )
    database.log_event(username, "signup", user_id)
    return _public_user(database.get_user_by_username(username)), []


def login(username, password):
    """Returns (user, error_message). Exactly one of them is None."""
    username = (username or "").strip()
    if not username or not password:
        return None, "Please enter your username and password."

    row = database.get_user_by_username(username)
    if row is None:
        database.log_event(username, "failed")
        return None, "Wrong username or password."  # same text: do not reveal which part failed

    # Is the account locked?
    if row["locked_until"] and datetime.fromisoformat(row["locked_until"]) > datetime.now():
        database.log_event(username, "locked", row["id"])
        return None, f"Too many wrong attempts. Account locked for {LOCK_MINUTES} minutes."

    if not verify_password(password, row["password_hash"]):
        just_locked = database.register_failed_attempt(row["id"], MAX_FAILED_ATTEMPTS, LOCK_MINUTES)
        database.log_event(username, "locked" if just_locked else "failed", row["id"])
        if just_locked:
            return None, f"Too many wrong attempts. Account locked for {LOCK_MINUTES} minutes."
        return None, "Wrong username or password."

    database.mark_login_success(row["id"])
    database.log_event(username, "login", row["id"])
    return _public_user(row), None


def logout(user: dict):
    database.log_event(user["username"], "logout", user["id"])