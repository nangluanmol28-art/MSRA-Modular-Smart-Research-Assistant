import pytest
from unittest.mock import patch
from src.llm import (
    get_llm,
    LLMAuthError,
    LLMQuotaError,
    LLMError
)


@pytest.mark.doom
class TestDoomFailureInjection:

    def test_invalid_api_key_raises_auth_error(self, monkeypatch):
        import src.llm
        monkeypatch.setattr(src.llm, "get_api_key", lambda name: None)
        with pytest.raises(LLMAuthError):
            get_llm("test question", provider="Google Gemini", enable_fallback=False)

    def test_quota_429_exhaustion_raises_quota_error(self):
        with patch("src.llm.call_gemini", side_effect=LLMQuotaError("HTTP 429 Quota Exceeded")):
            with pytest.raises(LLMQuotaError):
                get_llm("test question", provider="Google Gemini", enable_fallback=False)

    def test_primary_fail_triggers_secondary_fallback(self):
        with patch("src.llm.call_gemini", side_effect=LLMError("Gemini server 500 error")):
            with patch("src.llm.call_groq", return_value="Fallback response from Groq [1]"):
                ans, prov, is_fb = get_llm("test question", provider="Google Gemini", enable_fallback=True)
                assert is_fb is True
                assert "Groq" in prov
                assert "Fallback response from Groq" in ans

    def test_both_models_failing_raises_clean_exception(self):
        with patch("src.llm.call_gemini", side_effect=LLMError("Gemini server 500 error")):
            with patch("src.llm.call_groq", side_effect=LLMError("Groq server 500 error")):
                with pytest.raises(LLMError) as exc_info:
                    get_llm("test question", provider="Google Gemini", enable_fallback=True)
                assert "failed" in str(exc_info.value).lower()
