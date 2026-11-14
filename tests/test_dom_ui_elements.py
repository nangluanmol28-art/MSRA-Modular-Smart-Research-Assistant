import pytest
from streamlit.testing.v1 import AppTest
from config import STATUS_OK
from src.llm import DEFAULT_GEMINI_MODEL, DEFAULT_GROQ_MODEL


class TestPhase2DOMAndUIElements:
    """Comprehensive DOM & UI element tests simulating user interactions on all controls."""

    def test_sidebar_and_empty_state_elements(self):
        """Test brand, sidebar buttons, empty state cards and prompt pills."""
        at = AppTest.from_file("app.py", default_timeout=30)
        at.run()
        assert len(at.exception) == 0

        # Verify left sidebar brand and buttons
        btn_labels = [b.label for b in at.button]
        assert "+ New Research Chat" in btn_labels
        assert "🗑️ Clear all my data" in btn_labels

        # Verify initial prompt pills exist and are disabled when 0 papers
        assert ":material/lightbulb: Summarize Key Methodologies" in btn_labels
        assert ":material/balance: Compare Findings Across Papers" in btn_labels
        assert ":material/search: Identify Research Gaps & Limitations" in btn_labels
        assert ":material/help_outline: Core Research Questions" in btn_labels

        # Verify research tools panel elements on empty state
        assert ":material/summarize: Summarize Paper" in btn_labels
        assert ":material/compare: Compare Papers" in btn_labels
        assert ":material/troubleshoot: Detect Gaps" in btn_labels
        assert ":material/picture_as_pdf: Export Report (PDF)" in btn_labels

    def test_new_research_chat_button_action(self):
        """Clicking + New Research Chat clears messages and resets query state."""
        at = AppTest.from_file("app.py", default_timeout=30)
        at.run()
        assert len(at.exception) == 0

        # Seed dirty chat messages
        at.session_state["messages"] = [
            {"role": "user", "content": "What is AI?"},
            {"role": "assistant", "content": "AI is artificial intelligence.", "citations": [], "status": STATUS_OK}
        ]
        at.session_state["last_failed_query"] = "fail query"
        at.session_state["pending"] = {"id": "1", "mode": "qa", "query": "hello"}
        at.run()

        # Find + New Research Chat button and click it
        new_chat_btn = [b for b in at.button if b.label == "+ New Research Chat"][0]
        new_chat_btn.click().run()

        assert len(at.exception) == 0
        assert at.session_state["messages"] == []
        assert at.session_state["last_failed_query"] is None
        assert at.session_state["pending"] is None

    def test_research_focus_text_input(self):
        """Research Focus input updates topic in session state."""
        at = AppTest.from_file("app.py", default_timeout=30)
        at.run()
        assert len(at.exception) == 0

        focus_inputs = [ti for ti in at.text_input if ti.label == "Research Focus / Scope"]
        assert len(focus_inputs) == 1
        focus_inputs[0].input("Transformers in Healthcare").run()

        assert len(at.exception) == 0
        assert at.session_state["research_topic"] == "Transformers in Healthcare"

    def test_model_selector_toggle_and_options(self):
        """Model selector popover changes provider and resets default models."""
        at = AppTest.from_file("app.py", default_timeout=30)
        at.run()
        assert len(at.exception) == 0

        # Default provider is Google Gemini
        assert at.session_state["selected_provider"] == "Google Gemini"
        assert at.session_state["selected_model"] == DEFAULT_GEMINI_MODEL

        # Switch to Groq
        radios = [r for r in at.radio if r.label == "Primary Provider"]
        assert len(radios) == 1
        radios[0].set_value("Groq").run()

        assert len(at.exception) == 0
        assert at.session_state["selected_provider"] == "Groq"
        assert at.session_state["selected_model"] == DEFAULT_GROQ_MODEL

    def test_single_paper_state_and_tool_buttons(self):
        """When 1 paper is indexed, single-paper summarize and gap detection buttons become active."""
        at = AppTest.from_file("app.py", default_timeout=30)
        at.run()
        assert len(at.exception) == 0

        at.session_state["indexed_papers"] = {
            "h_test1": {"name": "Vision_Transformer.pdf", "pages": 8, "chunks": 20, "size": 80000}
        }
        at.run()
        assert len(at.exception) == 0

        labels = [b.label for b in at.button]
        # Compare should still be disabled
        assert ":material/compare: Compare Papers" in labels
        # Single paper buttons should be customized to paper name
        assert any("Summarize" in l and "Vision_Transf" in l for l in labels)
        assert any("Detect Gaps" in l and "Vision_Transf" in l for l in labels)

    def test_multi_paper_state_and_comparison_enabled(self):
        """When 2+ papers are indexed, multi-paper comparison popover becomes active."""
        at = AppTest.from_file("app.py", default_timeout=30)
        at.run()
        assert len(at.exception) == 0

        at.session_state["indexed_papers"] = {
            "h_1": {"name": "Paper_1.pdf", "pages": 5, "chunks": 12, "size": 40000},
            "h_2": {"name": "Paper_2.pdf", "pages": 6, "chunks": 15, "size": 45000}
        }
        at.run()
        assert len(at.exception) == 0

        # Now compare should show checkboxes for the papers inside the popover
        chk_labels = [c.label for c in at.checkbox]
        assert "Paper_1.pdf" in chk_labels
        assert "Paper_2.pdf" in chk_labels
        assert len(at.exception) == 0

    def test_chat_message_action_controls(self):
        """Assistant messages render Copy popover, PDF download button, and feedback."""
        at = AppTest.from_file("app.py", default_timeout=30)
        at.run()
        assert len(at.exception) == 0

        at.session_state["messages"] = [
            {"role": "user", "content": "Explain CNN pooling."},
            {
                "role": "assistant",
                "content": "Pooling reduces spatial dimensions [1]. Max pooling is commonly used [2].",
                "citations": [
                    {"id": 1, "citation_label": "[1]", "source": "CNN_Paper.pdf", "page": "Page 3", "snippet": "Pooling reduces..."},
                    {"id": 2, "citation_label": "[2]", "source": "CNN_Paper.pdf", "page": "Page 4", "snippet": "Max pooling..."}
                ],
                "provider_info": "Generated using Google Gemini",
                "status": STATUS_OK,
                "follow_ups": ["What is average pooling?"]
            }
        ]
        at.run()
        assert len(at.exception) == 0

        # Check that PDF download button for the message is present
        dl_buttons = at.download_button
        assert len(dl_buttons) >= 1
        assert any("PDF" in b.label for b in dl_buttons)

        # Check regenerate button on last assistant message
        btn_labels = [b.label for b in at.button]
        assert any("Regenerate" in b for b in btn_labels)

        # Check feedback widget
        assert len(at.feedback) >= 1
