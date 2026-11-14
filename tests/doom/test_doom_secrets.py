import io
import sys
import pytest
from utils.errors import safe_log


@pytest.mark.doom
class TestDoomSecrets:

    def test_safe_log_redacts_gemini_and_groq_keys(self, monkeypatch):
        captured_err = io.StringIO()
        monkeypatch.setattr(sys, "stderr", captured_err)

        # Simulate exception containing real-looking API key strings
        fake_err = Exception("Failed calling https://api.groq.com with key gsk_1234567890abcdef and AIzaSyDDummyKey123")
        safe_log("TestContext", fake_err)

        log_output = captured_err.getvalue()
        assert "gsk_1234567890abcdef" not in log_output
        assert "AIzaSyDDummyKey123" not in log_output
        assert "[REDACTED_API_KEY]" in log_output
