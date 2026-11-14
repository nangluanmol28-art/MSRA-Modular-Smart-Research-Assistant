import json
import time
import requests
from config import get_api_key

# Supported Verified Models
GEMINI_MODELS = [
    "gemini-2.5-flash",
    "gemini-2.5-pro",
    "gemini-2.5-flash-lite",
    "gemini-1.5-flash",
    "gemini-1.5-pro"
]
DEFAULT_GEMINI_MODEL = "gemini-2.5-flash"

GROQ_MODELS = [
    "qwen/qwen3.8-27b",
    "openai/gpt-oss-120b",
    "openai/gpt-oss-20b"
]
DEFAULT_GROQ_MODEL = "qwen/qwen3.8-27b"

# Explicit Model ID -> Clean Human-Friendly Display Name Mapping
MODEL_DISPLAY_NAMES = {
    # Gemini Models
    "gemini-2.5-flash": "Gemini 2.5 Flash",
    "gemini-2.5-pro": "Gemini 2.5 Pro",
    "gemini-2.5-flash-lite": "Gemini 2.5 Flash Lite",
    "gemini-1.5-flash": "Gemini 1.5 Flash",
    "gemini-1.5-pro": "Gemini 1.5 Pro",
    # Groq Models
    "qwen/qwen3.8-27b": "Qwen 3.8 27B",
    "openai/gpt-oss-120b": "GPT-OSS 120B",
    "openai/gpt-oss-20b": "GPT-OSS 20B"
}


def get_model_display_name(model_id: str) -> str:
    """Returns human-friendly display name for a model id using an explicit mapping."""
    if not model_id:
        return "Unknown Model"
    return MODEL_DISPLAY_NAMES.get(model_id, model_id)


class LLMQuotaError(Exception):
    """Raised when rate limit (HTTP 429) or quota limit is reached."""
    pass


class LLMAuthError(Exception):
    """Raised when API key is missing or invalid (HTTP 401/403)."""
    pass


class LLMError(Exception):
    """Raised when an unrecoverable LLM API error occurs."""
    pass


def _build_gemini_config(model_name: str) -> dict:
    cfg = {
        "temperature": 0.25,
        "maxOutputTokens": 4096
    }
    # Turn off thinking budget on flash & flash-lite to conserve output tokens
    if "flash" in model_name and "pro" not in model_name:
        cfg["thinkingConfig"] = {"thinkingBudget": 0}
    return cfg


def call_gemini_single_attempt(prompt: str, model_name: str) -> str:
    """Performs a single generation request to Gemini."""
    key = get_api_key("GEMINI_API_KEY")
    if not key:
        raise LLMAuthError("Gemini API key is missing. Please add it to Streamlit secrets or your .env file.")

    headers = {
        "Content-Type": "application/json",
        "x-goog-api-key": key
    }
    data = {
        "contents": [
            {
                "role": "user",
                "parts": [{"text": prompt}]
            }
        ],
        "generationConfig": _build_gemini_config(model_name)
    }

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent"
    try:
        response = requests.post(url, headers=headers, json=data, timeout=6.0)
    except (requests.ConnectionError, requests.Timeout) as conn_err:
        raise LLMError(f"Gemini connection error: {str(conn_err)}")

    if response.status_code == 429:
        raise LLMQuotaError("Google Gemini API quota or rate limit exceeded (HTTP 429).")
    elif response.status_code in (401, 403):
        raise LLMAuthError(f"Google Gemini authentication failed (HTTP {response.status_code}).")
    elif response.status_code == 200:
        res = response.json()
        try:
            candidates = res.get("candidates", [])
            if not candidates:
                raise LLMError("Gemini returned an empty candidates list.")
            text = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "")
            finish_reason = candidates[0].get("finishReason", "")
            if not text.strip() and finish_reason != "MAX_TOKENS":
                raise LLMError("Gemini returned empty response text.")
            return text
        except (KeyError, IndexError):
            raise LLMError("Unexpected response structure from Gemini API.")
    else:
        raise LLMError(f"Gemini API HTTP {response.status_code}: {response.text}")


def call_gemini(prompt: str, model_name: str = None) -> str:
    """Call Google Gemini API with immediate fallback on 429 and fast failover."""
    m = model_name or DEFAULT_GEMINI_MODEL
    try:
        return call_gemini_single_attempt(prompt, m)
    except (LLMAuthError, LLMQuotaError) as immediate_err:
        raise immediate_err
    except Exception as e:
        raise LLMError(f"Failed to generate response from Gemini: {e}")


def stream_gemini(prompt: str, model_name: str = None):
    """Streams response from Google Gemini API token-by-token."""
    key = get_api_key("GEMINI_API_KEY")
    if not key:
        raise LLMAuthError("Gemini API key is missing. Please add it to Streamlit secrets or your .env file.")

    headers = {
        "Content-Type": "application/json",
        "x-goog-api-key": key
    }
    m = model_name or DEFAULT_GEMINI_MODEL
    data = {
        "contents": [
            {
                "role": "user",
                "parts": [{"text": prompt}]
            }
        ],
        "generationConfig": _build_gemini_config(m)
    }

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{m}:streamGenerateContent?alt=sse"
    try:
        response = requests.post(url, headers=headers, json=data, stream=True, timeout=6.0)
    except (requests.ConnectionError, requests.Timeout) as e:
        raise LLMError(f"Gemini connection error: {str(e)}")

    if response.status_code == 429:
        raise LLMQuotaError("Google Gemini API quota or rate limit exceeded (HTTP 429).")
    elif response.status_code in (401, 403):
        raise LLMAuthError(f"Google Gemini authentication failed (HTTP {response.status_code}).")
    elif response.status_code != 200:
        raise LLMError(f"Gemini streaming API HTTP {response.status_code}: {response.text}")

    has_yielded = False
    for line in response.iter_lines():
        if line:
            decoded = line.decode("utf-8").strip()
            if decoded.startswith("data: "):
                data_json = decoded[6:]
                try:
                    chunk = json.loads(data_json)
                    text = chunk["candidates"][0]["content"]["parts"][0].get("text", "")
                    if text:
                        has_yielded = True
                        yield text
                except (KeyError, IndexError, json.JSONDecodeError):
                    continue
    if not has_yielded:
        raise LLMError("Gemini returned an empty stream.")


def call_groq(prompt: str, model_name: str = None) -> str:
    """Call Groq API via OpenAI-compatible chat completions endpoint."""
    key = get_api_key("GROQ_API_KEY")
    if not key:
        raise LLMAuthError("Groq API key is missing. Please add it to Streamlit secrets or your .env file.")

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {key}"
    }

    models_to_try = [model_name] if model_name else []
    for m in GROQ_MODELS:
        if m not in models_to_try:
            models_to_try.append(m)

    last_error = None
    for m in models_to_try:
        payload = {
            "model": m,
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.25,
            "max_tokens": 4096
        }
        try:
            response = requests.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=30
            )
            if response.status_code == 429:
                raise LLMQuotaError("Groq API rate limit or quota exceeded (HTTP 429).")
            elif response.status_code in (401, 403):
                raise LLMAuthError(f"Groq authentication failed (HTTP {response.status_code}).")
            elif response.status_code == 200:
                res = response.json()
                try:
                    return res["choices"][0]["message"]["content"]
                except (KeyError, IndexError):
                    raise LLMError("Unexpected response format from Groq API.")
            elif response.status_code == 404:
                last_error = f"Groq Model {m} not found."
                continue
            else:
                last_error = f"Groq API HTTP {response.status_code}: {response.text}"
        except (LLMQuotaError, LLMAuthError) as direct_err:
            raise direct_err
        except Exception as e:
            last_error = str(e)

    if last_error and "quota" in str(last_error).lower():
        raise LLMQuotaError(last_error)
    raise LLMError(f"Failed to generate response from Groq: {last_error}")


def stream_groq(prompt: str, model_name: str = None):
    """Streams response from Groq API token-by-token with automatic model-level fallback on 404."""
    key = get_api_key("GROQ_API_KEY")
    if not key:
        raise LLMAuthError("Groq API key is missing. Please add it to Streamlit secrets or your .env file.")

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {key}"
    }

    models_to_try = [model_name] if model_name else []
    for m in GROQ_MODELS:
        if m not in models_to_try:
            models_to_try.append(m)

    last_error = None
    for m in models_to_try:
        payload = {
            "model": m,
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.25,
            "max_tokens": 4096,
            "stream": True
        }
        try:
            response = requests.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers=headers,
                json=payload,
                stream=True,
                timeout=30
            )
        except (requests.ConnectionError, requests.Timeout) as e:
            last_error = f"Groq connection error: {str(e)}"
            continue

        if response.status_code == 429:
            raise LLMQuotaError("Groq API rate limit or quota exceeded (HTTP 429).")
        elif response.status_code in (401, 403):
            raise LLMAuthError(f"Groq authentication failed (HTTP {response.status_code}).")
        elif response.status_code == 404:
            last_error = f"Groq Model {m} not found (HTTP 404)."
            continue
        elif response.status_code != 200:
            last_error = f"Groq streaming API HTTP {response.status_code}: {response.text}"
            continue

        has_yielded = False
        for line in response.iter_lines():
            if line:
                decoded = line.decode("utf-8").strip()
                if decoded.startswith("data: "):
                    data_str = decoded[6:]
                    if data_str == "[DONE]":
                        break
                    try:
                        chunk = json.loads(data_str)
                        delta = chunk["choices"][0].get("delta", {}).get("content", "")
                        if delta:
                            has_yielded = True
                            yield delta
                    except (KeyError, IndexError, json.JSONDecodeError):
                        continue
        if has_yielded:
            return
        last_error = "Groq returned an empty stream."

    if last_error:
        raise LLMError(last_error)


def get_llm(
    prompt: str,
    provider: str = "Google Gemini",
    model_name: str = None,
    enable_fallback: bool = True
) -> tuple[str, str, bool]:
    """
    Primary synchronous LLM router supporting provider selection and automatic fallback.
    Returns (response_text, provider_used, is_fallback_boolean).
    """
    is_gemini_primary = "gemini" in provider.lower()

    if is_gemini_primary:
        prim_m = model_name or DEFAULT_GEMINI_MODEL
        fb_m = DEFAULT_GROQ_MODEL
        primary_fn = lambda: call_gemini(prompt, prim_m)
        primary_name = f"Google Gemini ({get_model_display_name(prim_m)})"
        fallback_fn = lambda: call_groq(prompt, fb_m)
        fallback_name = f"Groq ({get_model_display_name(fb_m)}) after Gemini failed"
    else:
        prim_m = model_name or DEFAULT_GROQ_MODEL
        fb_m = DEFAULT_GEMINI_MODEL
        primary_fn = lambda: call_groq(prompt, prim_m)
        primary_name = f"Groq ({get_model_display_name(prim_m)})"
        fallback_fn = lambda: call_gemini(prompt, fb_m)
        fallback_name = f"Google Gemini ({get_model_display_name(fb_m)}) after Groq failed"

    # Attempt Primary Provider
    try:
        text = primary_fn()
        return text, primary_name, False
    except (LLMQuotaError, LLMError, Exception) as primary_err:
        if not enable_fallback:
            raise primary_err

        # Attempt Fallback Provider
        try:
            fallback_text = fallback_fn()
            return fallback_text, fallback_name, True
        except LLMAuthError as fb_auth_err:
            raise LLMQuotaError(
                f"{primary_name} failed ({str(primary_err)}). Fallback to {fallback_name} failed: {str(fb_auth_err)}"
            )
        except LLMQuotaError:
            raise LLMQuotaError(
                f"Both {primary_name} and {fallback_name} quota limits have been exhausted."
            )
        except Exception as fb_err:
            raise LLMError(
                f"{primary_name} failed ({str(primary_err)}). Fallback attempt failed: {str(fb_err)}"
            )


def stream_llm(
    prompt: str,
    provider: str = "Google Gemini",
    model_name: str = None,
    enable_fallback: bool = True
):
    """
    Generator streaming tokens with automatic fallback support.
    Yields (token, provider_used, is_fallback).
    Peeks first token before committing to primary.
    """
    is_gemini_primary = "gemini" in provider.lower()

    if is_gemini_primary:
        prim_m = model_name or DEFAULT_GEMINI_MODEL
        fb_m = DEFAULT_GROQ_MODEL
        primary_gen = lambda: stream_gemini(prompt, prim_m)
        primary_name = f"Google Gemini ({get_model_display_name(prim_m)})"
        fallback_gen = lambda: stream_groq(prompt, fb_m)
        fallback_name = f"Groq ({get_model_display_name(fb_m)}) after Gemini failed"
    else:
        prim_m = model_name or DEFAULT_GROQ_MODEL
        fb_m = DEFAULT_GEMINI_MODEL
        primary_gen = lambda: stream_groq(prompt, prim_m)
        primary_name = f"Groq ({get_model_display_name(prim_m)})"
        fallback_gen = lambda: stream_gemini(prompt, fb_m)
        fallback_name = f"Google Gemini ({get_model_display_name(fb_m)}) after Groq failed"

    # Peek the first token of the primary stream
    first_token = None
    try:
        primary_iter = primary_gen()
        first_token = next(primary_iter)
    except (StopIteration, Exception) as prim_fail:
        if not enable_fallback:
            raise prim_fail

        # Commit to fallback since primary failed before yielding any tokens
        try:
            for token in fallback_gen():
                yield token, fallback_name, True
            return
        except Exception as fb_fail:
            raise LLMError(f"{primary_name} failed ({str(prim_fail)}). Fallback to {fallback_name} failed: {str(fb_fail)}")

    # Yield verified first token
    yield first_token, primary_name, False

    # Continue remainder of primary stream
    try:
        for token in primary_iter:
            yield token, primary_name, False
    except Exception as mid_stream_err:
        # Partial output was already rendered: DO NOT concatenate fallback response!
        yield "\n\n⚠️ *Response interrupted. Click Regenerate to retry.*", primary_name, False
        return
