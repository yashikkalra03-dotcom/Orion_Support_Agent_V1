import os
from pathlib import Path

import httpx
from dotenv import load_dotenv

ENV_PATH = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=ENV_PATH, override=True)

APP_NAME = "ORION"
APP_TAGLINE = "Autonomous Customer Intelligence System"
FOOTER = "Created by: Yashik Kalra"
DEFAULT_MODEL_NAME = "gemini-3.5-flash-lite"
GEMINI_API_BASE_URL = "https://generativelanguage.googleapis.com/v1beta"


def _load_env() -> None:
    load_dotenv(dotenv_path=ENV_PATH, override=True)


def get_model_name() -> str:
    _load_env()
    return (
        os.getenv("GOOGLE_MODEL")
        or os.getenv("GEMINI_MODEL")
        or os.getenv("Gemini_MODEL")
        or os.getenv("MODEL_NAME")
        or DEFAULT_MODEL_NAME
    ).strip()


MODEL_NAME = get_model_name()
GEMINI_API_URL = f"{GEMINI_API_BASE_URL}/models/{MODEL_NAME}:generateContent"


def get_google_api_key() -> str:
    _load_env()
    return (
        os.getenv("GOOGLE_API_KEY")
        or os.getenv("GEMINI_API_KEY")
        or os.getenv("Gemini_API_KEY")
        or ""
    ).strip()


def _is_placeholder_key(value: str) -> bool:
    cleaned = (value or "").strip().lower()
    return not cleaned or cleaned in {
        "your_api_key_here",
        "placeholder",
        "demo",
        "example",
        "test_key",
        "replace_me",
        "changeme",
    }


def is_api_configured() -> bool:
    return not _is_placeholder_key(get_google_api_key())


def is_llm_configured() -> bool:
    return is_api_configured()


def validate_gemini_connection(
    api_key: str | None = None,
) -> tuple[bool, bool, bool, bool, str]:
    key = (api_key if api_key is not None else get_google_api_key()).strip()
    if _is_placeholder_key(key):
        return False, False, False, False, "GOOGLE_API_KEY is missing from .env or is a placeholder."

    api_connected = False
    try:
        connection = httpx.get(
            f"{GEMINI_API_BASE_URL}/models",
            headers={"x-goog-api-key": key},
            timeout=15,
        )
        api_connected = connection.status_code == 200
        if connection.status_code != 200:
            try:
                error = connection.json().get("error", {})
                detail = str(error.get("message") or connection.text).replace(key, "[redacted]")[:1000]
                status = str(error.get("status", ""))
            except ValueError:
                detail = connection.text.replace(key, "[redacted]")[:1000]
                status = ""
            invalid_key = connection.status_code in {401, 403} or (
                status == "INVALID_ARGUMENT" and "api key" in detail.lower()
            )
            prefix = "Invalid Gemini API Key" if invalid_key else f"Gemini HTTP {connection.status_code}"
            return True, False, False, invalid_key, f"{prefix}: {detail}"

        payload = connection.json()
        models = payload.get("models", []) if isinstance(payload, dict) else []
        model_name = get_model_name()
        available = {
            str(model.get("name", "")).removeprefix("models/"): model
            for model in models
            if isinstance(model, dict)
        }
        model = available.get(model_name)
        if model is None:
            return True, True, False, False, f"Gemini connected, but model '{model_name}' is not available to this API key."
        methods = model.get("supportedGenerationMethods", [])
        if "generateContent" not in methods:
            return True, True, False, False, f"Gemini model '{model_name}' does not support generateContent."

        response = httpx.post(
            f"{GEMINI_API_BASE_URL}/models/{model_name}:generateContent",
            headers={"x-goog-api-key": key},
            json={
                "contents": [{"parts": [{"text": "Reply with exactly: Gemini connection test passed."}]}],
                "generationConfig": {"maxOutputTokens": 32},
            },
            timeout=45,
        )
        if response.status_code != 200:
            try:
                error = response.json().get("error", {})
                detail = str(error.get("message") or response.text).replace(key, "[redacted]")[:1000]
                status = str(error.get("status", ""))
            except ValueError:
                detail = response.text.replace(key, "[redacted]")[:1000]
                status = ""
            invalid_key = response.status_code in {401, 403} or (
                status == "INVALID_ARGUMENT" and "api key" in detail.lower()
            )
            prefix = "Invalid Gemini API Key" if invalid_key else f"Gemini test request failed (HTTP {response.status_code})"
            return True, True, False, invalid_key, f"{prefix}: {detail}"

        payload = response.json()
        candidates = payload.get("candidates", [])
        text = "".join(
            str(part.get("text", ""))
            for part in candidates[0].get("content", {}).get("parts", [])
            if isinstance(part, dict)
        ) if candidates else ""
        if not text.strip():
            return True, True, False, False, "Gemini connected but the startup test returned no text."
        return True, True, True, False, "Gemini Connected Successfully"
    except httpx.HTTPError as exc:
        return True, api_connected, False, False, f"Gemini request failed: {type(exc).__name__}: {exc}"
    except (TypeError, ValueError, KeyError) as exc:
        return True, api_connected, False, False, f"Invalid Gemini response: {type(exc).__name__}: {exc}"
