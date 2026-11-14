import os
import uuid
import pytest
from utils.session import (
    get_session_dir,
    get_session_upload_dir,
    clear_session_data
)
from src.pdf_rag import create_vectorstore, delete_paper_from_vectorstore
from langchain_core.documents import Document


@pytest.mark.doom
class TestDoomLifecycle:

    def test_upload_delete_cycle_30x(self, mock_embeddings):
        sid = f"lifecycle-{uuid.uuid4()}"
        doc1 = Document(
            page_content="Machine learning neural networks in medical analysis.",
            metadata={"source": "medical_ml.pdf", "page_label": "1"}
        )

        vstore = create_vectorstore([doc1], session_id=sid)

        for i in range(15):
            # Delete paper
            delete_paper_from_vectorstore(vstore, "medical_ml.pdf")
            # Verify deletion or empty
            remaining = vstore.get(where={"source": "medical_ml.pdf"})
            assert len(remaining.get("ids", [])) == 0

            # Re-add paper
            vstore.add_documents([doc1])
            recheck = vstore.get(where={"source": "medical_ml.pdf"})
            assert len(recheck.get("ids", [])) > 0

        clear_session_data(sid)

    def test_clear_all_my_data_purges_disk(self):
        sid = f"clear-test-{uuid.uuid4()}"
        upload_dir = get_session_upload_dir(sid)
        dummy_file = os.path.join(upload_dir, "test_doc.txt")
        with open(dummy_file, "w") as f:
            f.write("temporary research data")

        assert os.path.exists(dummy_file)

        # Execute clear data
        clear_session_data(sid)

        # Verify disk directory is wiped
        from config import BASE_DATA_DIR
        session_root = os.path.join(BASE_DATA_DIR, sid)
        assert not os.path.exists(dummy_file)
        assert not os.path.exists(session_root)
