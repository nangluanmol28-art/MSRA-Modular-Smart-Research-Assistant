import os
import uuid
import pytest
from concurrent.futures import ThreadPoolExecutor
from utils.session import get_session_dir, get_session_upload_dir, get_session_chroma_dir, clear_session_data
from src.pdf_rag import create_vectorstore
from langchain_core.documents import Document


@pytest.mark.doom
class TestDoomConcurrency:

    def test_20_simulated_sessions_path_isolation(self):
        sessions = [str(uuid.uuid4()) for _ in range(20)]
        session_dirs = [get_session_dir(s) for s in sessions]
        upload_dirs = [get_session_upload_dir(s) for s in sessions]
        chroma_dirs = [get_session_chroma_dir(s) for s in sessions]

        # Verify all directories are strictly unique
        assert len(set(session_dirs)) == 20
        assert len(set(upload_dirs)) == 20
        assert len(set(chroma_dirs)) == 20

        for u_dir in upload_dirs:
            assert os.path.exists(u_dir)

    def test_concurrent_sessions_vectorstore_isolation(self, mock_embeddings):
        num_sessions = 5

        def run_session_indexing(session_idx):
            sid = f"concurrent-sess-{session_idx}-{uuid.uuid4()}"
            doc = Document(
                page_content=f"Secret paper content for unique session {session_idx} only.",
                metadata={"source": f"paper_{session_idx}.pdf", "page_label": "1"}
            )
            vstore = create_vectorstore([doc], session_id=sid)
            # Retrieve from this session's store
            retrieved = vstore.similarity_search(f"session {session_idx}", k=1)
            assert len(retrieved) > 0
            assert f"session {session_idx}" in retrieved[0].page_content
            # Cleanup
            clear_session_data(sid)
            return True

        with ThreadPoolExecutor(max_workers=num_sessions) as executor:
            futures = [executor.submit(run_session_indexing, i) for i in range(num_sessions)]
            results = [f.result() for f in futures]

        assert all(results)
