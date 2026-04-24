"""
Firebase ID token verification helpers.
Supports both local (file path) and cloud (base64 JSON env var) credentials.
"""

from __future__ import annotations

import base64
import json
import os
from functools import lru_cache

import firebase_admin
from firebase_admin import auth as firebase_auth
from firebase_admin import credentials

from app.core.config import settings


@lru_cache(maxsize=1)
def _get_firebase_app() -> firebase_admin.App:
    """Initialize Firebase app once.

    Credential resolution order:
    1. FIREBASE_CREDENTIALS_JSON  — base64-encoded JSON string (cloud / Railway)
    2. FIREBASE_CREDENTIALS_PATH  — path to service account JSON file (local dev)
    3. Application Default Credentials (GOOGLE_APPLICATION_CREDENTIALS env var)
    """
    # 1. Base64-encoded JSON from environment variable (production / Railway)
    if settings.FIREBASE_CREDENTIALS_JSON:
        try:
            raw_json = base64.b64decode(settings.FIREBASE_CREDENTIALS_JSON).decode("utf-8")
            cred_dict = json.loads(raw_json)
            cred = credentials.Certificate(cred_dict)
            return firebase_admin.initialize_app(cred)
        except Exception as exc:
            raise RuntimeError(
                f"Failed to load Firebase credentials from FIREBASE_CREDENTIALS_JSON: {exc}"
            ) from exc

    # 2. File path (local development)
    if settings.FIREBASE_CREDENTIALS_PATH:
        cred = credentials.Certificate(settings.FIREBASE_CREDENTIALS_PATH)
        return firebase_admin.initialize_app(cred)

    # 3. Application Default Credentials
    return firebase_admin.initialize_app()


def verify_firebase_id_token(id_token: str) -> dict:
    """Verify a Firebase ID token and return decoded claims."""
    app = _get_firebase_app()
    claims = firebase_auth.verify_id_token(id_token, app=app)

    if settings.FIREBASE_PROJECT_ID and claims.get("aud") != settings.FIREBASE_PROJECT_ID:
        raise ValueError("Invalid Firebase audience")

    return claims


def validate_firebase_startup() -> None:
    """
    Fail fast if Firebase verification is required but backend is misconfigured.
    """
    if not settings.FIREBASE_VERIFICATION_REQUIRED:
        return

    has_cred_json = bool(settings.FIREBASE_CREDENTIALS_JSON)
    has_cred_path = bool(settings.FIREBASE_CREDENTIALS_PATH)
    has_adc = bool(os.getenv("GOOGLE_APPLICATION_CREDENTIALS"))

    if not (has_cred_json or has_cred_path or has_adc):
        raise RuntimeError(
            "Firebase verification is required, but no credentials are configured. "
            "Set FIREBASE_CREDENTIALS_JSON (base64), FIREBASE_CREDENTIALS_PATH, "
            "or GOOGLE_APPLICATION_CREDENTIALS."
        )

    if not settings.FIREBASE_PROJECT_ID:
        raise RuntimeError(
            "Firebase verification is required, but FIREBASE_PROJECT_ID is missing."
        )

    # Initialize the app at startup to detect invalid credential config early.
    _get_firebase_app()
