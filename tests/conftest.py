import os
import sys
import hashlib
import pytest
from typing import List

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _root not in sys.path:
    sys.path.insert(0, _root)

_venv_site = os.path.join(_root, ".myenv", "Lib", "site-packages")
if os.path.exists(_venv_site) and _venv_site not in sys.path:
    sys.path.insert(0, _venv_site)


class FastDeterministicEmbeddings:
    """Deterministic 384-dim normalized mock embeddings running in 0.0001s without torch or HF model download."""
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        return [self._hash_vector(t) for t in texts]

    def embed_query(self, text: str) -> List[float]:
        return self._hash_vector(text)

    def _hash_vector(self, text: str) -> List[float]:
        seed = int(hashlib.md5(text.encode("utf-8", errors="replace")).hexdigest(), 16)
        vec = [((seed + i * 31) % 1000) / 1000.0 for i in range(384)]
        norm = sum(x * x for x in vec) ** 0.5 or 1.0
        return [x / norm for x in vec]


@pytest.fixture(autouse=True)
def mock_embeddings(monkeypatch):
    fast_emb = FastDeterministicEmbeddings()
    import src.pdf_rag
    monkeypatch.setattr(src.pdf_rag, "get_embeddings", lambda: fast_emb)
    monkeypatch.setattr(src.pdf_rag, "_LazyEmbeddings", lambda: fast_emb)
    return fast_emb
