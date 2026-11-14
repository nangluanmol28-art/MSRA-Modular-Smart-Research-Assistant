# 📚 Modular Smart Research Assistant (MSRA)
## Project Specification & Architecture Overview

### Problem Statement
Students, researchers, and professionals spend a significant amount of time manually reading and searching through multiple research PDFs, survey papers, notes, and technical articles to synthesize relevant information. This process is time-consuming, prone to human error, and lacks unified cross-document synthesis.

### Solution & Objectives
MSRA delivers an AI-powered academic copilot that:
- Ingests and processes single or multiple research PDFs simultaneously.
- Indexes content with dense vector embeddings into ChromaDB with per-session isolation.
- Retrieves context-aware evidence chunks using Maximum Marginal Relevance (MMR) and similarity search.
- Generates rigorous research responses grounded with verifiable page-level inline citations `[1]`, `[2]`.
- Provides 4 dedicated research tools: Summarization, Comparison, Gap Detection, and Publication Export.
- Seamlessly falls back between LLM providers (Google Gemini and Groq) for uninterrupted research workflows.

---

### Pipeline Architecture

```
User Query / PDF Upload
         │
         ▼
[ PDF Ingestion Layer ]
  ├─ Integrity & Malware Validation (utils.errors)
  ├─ Page-Level Metadata Extraction (src.pdf_rag)
  └─ Text Chunking (RecursiveCharacterTextSplitter)
         │
         ▼
[ Vector Embedding & Indexing ]
  ├─ Embedding Model (sentence-transformers/all-MiniLM-L6-v2)
  └─ Isolated ChromaDB Vectorstore (data/sessions/<uuid>/chroma)
         │
         ▼
[ Retrieval & Synthesis Engine ]
  ├─ Query Condensation & Contextual Rewriting
  ├─ MMR Top-k Candidate Retrieval (src.chain)
  ├─ LLM Execution with Automatic Provider Fallback (src.llm)
  └─ Citation Normalization & Evidence Mapping (src.citations)
         │
         ▼
[ Output & Presentation Layer ]
  ├─ Interactive Streamlit Workspace (app.py)
  ├─ 3D Particle Canvas & Dark Mode Surface (src.background_3d)
  ├─ Sources Dropdown & Page Reference Verification
  └─ Academic PDF / DOCX Export Engine (src.export)
```
