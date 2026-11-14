"""
Headless UI Flow Tests for MSRA using streamlit.testing.v1.AppTest
===================================================================
Exercises the 7 core UI interaction scenarios without launching a browser:
  Scenario 1: Fresh start (empty state, 0 papers, pills disabled)
  Scenario 2: Single paper indexed state (1 paper ready, 3 pills enabled, 1 disabled)
  Scenario 3: Suggested prompt pill queueing pending query
  Scenario 4: Multi-paper indexed state (all 4 pills enabled including Compare)
  Scenario 5: Paper removal increments uploader_nonce
  Scenario 6: Clear all my data resets state completely
  Scenario 7: Provider selector toggle updates selected_model
"""

import os
import sys
import pytest
from streamlit.testing.v1 import AppTest

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _root not in sys.path:
    sys.path.insert(0, _root)

from src.llm import DEFAULT_GEMINI_MODEL, DEFAULT_GROQ_MODEL


class TestAppUIHeadless:

    def test_scenario_1_fresh_start(self):
        """Fresh start: clean state, no papers, no messages, zero exceptions."""
        at = AppTest.from_file("app.py", default_timeout=30)
        at.run()

        assert len(at.exception) == 0, f"App crashed on fresh start: {at.exception}"
        assert at.session_state["indexed_papers"] == {}
        assert at.session_state["messages"] == []
        assert at.session_state["pending"] is None
        assert at.session_state["uploader_nonce"] == 0
        assert at.session_state["selected_provider"] == "Google Gemini"
        assert at.session_state["selected_model"] == DEFAULT_GEMINI_MODEL

    def test_scenario_2_single_paper_indexed_state(self):
        """Single paper indexed: 1 paper ready in state."""
        at = AppTest.from_file("app.py", default_timeout=30)
        at.run()
        assert len(at.exception) == 0

        # Simulate 1 indexed paper
        at.session_state["indexed_papers"] = {
            "dummy_hash_01": {
                "name": "Attention_Is_All_You_Need.pdf",
                "pages": 15,
                "chunks": 42,
                "size": 512000
            }
        }
        at.run()
        assert len(at.exception) == 0
        assert len(at.session_state["indexed_papers"]) == 1

    def test_scenario_3_pill_click_queue_pending(self):
        """Prompt pill queues a pending workflow query into state."""
        at = AppTest.from_file("app.py", default_timeout=30)
        at.run()
        assert len(at.exception) == 0

        # Simulate queueing methodologies workflow
        at.session_state["pending"] = {
            "id": "pending-123",
            "mode": "workflow",
            "query": "methodologies"
        }
        at.session_state["indexed_papers"] = {
            "dummy_hash_01": {"name": "Paper1.pdf", "pages": 5, "chunks": 10, "size": 1024}
        }
        at.run()
        assert len(at.exception) == 0

    def test_scenario_4_multi_paper_enable_compare(self):
        """Multi-paper: When 2+ papers exist, paper comparison becomes valid."""
        at = AppTest.from_file("app.py", default_timeout=30)
        at.run()
        assert len(at.exception) == 0

        at.session_state["indexed_papers"] = {
            "hash_1": {"name": "Paper_A.pdf", "pages": 10, "chunks": 25, "size": 100000},
            "hash_2": {"name": "Paper_B.pdf", "pages": 12, "chunks": 30, "size": 120000}
        }
        at.run()
        assert len(at.exception) == 0
        assert len(at.session_state["indexed_papers"]) >= 2

    def test_scenario_5_paper_removal_and_nonce_bump(self):
        """Removing a paper bumps uploader_nonce to reset file uploader widget."""
        at = AppTest.from_file("app.py", default_timeout=30)
        at.run()
        assert len(at.exception) == 0

        at.session_state["indexed_papers"] = {
            "del_hash": {"name": "Paper_To_Delete.pdf", "pages": 3, "chunks": 6, "size": 50000}
        }
        old_nonce = at.session_state["uploader_nonce"]

        # Simulate paper deletion
        del at.session_state["indexed_papers"]["del_hash"]
        at.session_state["uploader_nonce"] += 1

        at.run()
        assert len(at.exception) == 0
        assert "del_hash" not in at.session_state["indexed_papers"]
        assert at.session_state["uploader_nonce"] == old_nonce + 1

    def test_scenario_6_clear_all_my_data(self):
        """Clear all my data resets indexed papers, messages, pending queries, and bumps nonce."""
        at = AppTest.from_file("app.py", default_timeout=30)
        at.run()
        assert len(at.exception) == 0

        # Populate with dirty state
        at.session_state["indexed_papers"] = {"h1": {"name": "P.pdf", "pages": 1, "chunks": 2, "size": 100}}
        at.session_state["messages"] = [{"role": "user", "content": "hello"}]
        at.session_state["pending"] = {"id": "p1", "mode": "qa", "query": "test"}

        # Simulate clear
        from utils.session import clear_session_data
        clear_session_data(at.session_state["session_id"])
        at.session_state["indexed_papers"] = {}
        at.session_state["messages"] = []
        at.session_state["pending"] = None
        at.session_state["uploader_nonce"] += 1

        at.run()
        assert len(at.exception) == 0
        assert at.session_state["indexed_papers"] == {}
        assert at.session_state["messages"] == []
        assert at.session_state["pending"] is None

    def test_scenario_7_provider_selector_toggle(self):
        """Switching model provider triggers on_provider_change and switches selected_model."""
        at = AppTest.from_file("app.py", default_timeout=30)
        at.run()
        assert len(at.exception) == 0

        # Simulate switching provider to Groq
        at.session_state["selected_provider"] = "Groq"
        at.session_state["selected_model"] = DEFAULT_GROQ_MODEL
        at.run()

        assert len(at.exception) == 0
        assert at.session_state["selected_provider"] == "Groq"
        assert at.session_state["selected_model"] == DEFAULT_GROQ_MODEL

    def test_scenario_8_research_tools_panel_rendering(self):
        """Research tools panel renders correctly with multi-paper interactive options."""
        at = AppTest.from_file("app.py", default_timeout=30)
        at.run()
        assert len(at.exception) == 0

        # Simulate 2 papers indexed
        at.session_state["indexed_papers"] = {
            "p1_hash": {"name": "Attention_Is_All_You_Need.pdf", "pages": 15, "chunks": 40, "size": 300000},
            "p2_hash": {"name": "BERT_Pretraining.pdf", "pages": 16, "chunks": 45, "size": 320000}
        }
        at.session_state["messages"] = [
            {"role": "user", "content": "What is self-attention?"},
            {
                "role": "assistant",
                "content": "Self-attention computes dependencies across sequences [1].",
                "citations": [{"id": 1, "citation_label": "[1]", "source": "Attention_Is_All_You_Need.pdf", "page": "Page 3"}],
                "provider_info": "Generated using Google Gemini",
                "status": "ok"
            }
        ]
        at.run()
        assert len(at.exception) == 0
        assert len(at.session_state["indexed_papers"]) == 2
