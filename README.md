# MSRA – Modular Smart Research Assistant

[![Python Version](https://img.shields.io/badge/Python-3.11%20%7C%203.12-blue.svg)](https://www.python.org/)
[![Streamlit](https://img.shields.io/badge/Frontend-Streamlit%201.35+-red.svg)](https://streamlit.io/)
[![LangChain](https://img.shields.io/badge/Orchestration-LangChain%200.2+-green.svg)](https://www.langchain.com/)
[![ChromaDB](https://img.shields.io/badge/Vector%20Store-ChromaDB%200.5+-purple.svg)](https://www.trychroma.com/)
[![Tests](https://img.shields.io/badge/Tests-100%20Passed-brightgreen.svg)](tests/)
[![Institution](https://img.shields.io/badge/Institution-SBBSU-orange.svg)](https://www.sbbsuniversity.ac.in/)

> **MSRA (Modular Smart Research Assistant)** is a high-performance academic research copilot designed to analyze, summarize, cross-compare, and synthesize insights across single and multiple research papers with verifiable sentence-level citations, zero-hallucination guarantees, and automatic multi-provider LLM failover.

---

## 📑 Table of Contents

1. [Project Overview](#1-project-overview)
2. [Key Features](#2-key-features)
3. [System Architecture](#3-system-architecture)
4. [Technologies Used](#4-technologies-used)
5. [Project Folder Structure](#5-project-folder-structure)
6. [Installation Instructions](#6-installation-instructions)
7. [Environment Variables](#7-environment-variables)
8. [Running the Application](#8-running-the-application)
9. [Running Automated Tests](#9-running-automated-tests)
10. [Deployment Options](#10-deployment-options)
11. [Security and Data Privacy](#11-security-and-data-privacy)
12. [System Limitations](#12-system-limitations)
13. [Future Scope](#13-future-scope)
14. [Author & Project Information](#14-author--project-information)

---

## 1. Project Overview

Students, researchers, and academic professionals spend an enormous amount of time searching through dense technical PDFs, literature reviews, and empirical studies to synthesize relevant findings. Conventional "chat with PDF" chatbots often struggle with academic rigor: they blur boundaries between separate documents, fail to provide precise page provenance, and hallucinate citations when information is missing.

**MSRA – Modular Smart Research Assistant** bridges this gap by acting as a purpose-built academic copilot that:
- Ingests and indexes single or multiple research papers simultaneously.
- Preserves 1-indexed page-level provenance through every stage of chunking and retrieval.
- Uses **Retrieval-Augmented Generation (RAG)** with Maximum Marginal Relevance (MMR) to retrieve diverse, highly relevant evidence chunks.
- Enforces a strict grounding prompt that outputs numbered inline citations (`[1]`, `[2]`) linked directly to source documents and page numbers.
- Provides 4 dedicated research tools: **Structured Paper Summarization**, **Multi-Paper Comparative Analysis**, **Research Gap Detection**, and **Publication-Ready Export (PDF & DOCX)**.
- Maintains high availability through an intelligent dual-provider gateway supporting **Google Gemini** and **Groq** with automatic zero-downtime quota failover.

---

## 2. Key Features

### 📄 PDF-Based Research Chat
- Engage in a natural language research dialogue grounded directly in uploaded literature.
- Contextual query condensation automatically rewrites follow-up questions using conversation history before retrieval.
- Grounded refusal: If a query cannot be answered from the uploaded papers, MSRA explicitly states: *"I couldn't find this in the uploaded papers"* rather than generating ungrounded claims.

### 📚 Single-PDF and Multi-PDF Support
- Upload and index up to 5 research papers per session (up to 25 MB per file, max 300 total pages).
- Multi-document retrieval allows cross-paper synthesis across different authors, methodologies, and datasets.
- Interactive paper manager in the sidebar displays page counts, chunk counts, and file sizes, with 1-click individual document deletion.

### 📝 Research Paper Summarization
- Generates a rigorous, structured 9-part academic summary for any indexed paper:
  1. *Paper Title & Overview*
  2. *Research Objective & Problem Statement*
  3. *Methodology & System Architecture*
  4. *Datasets, Benchmarks & Baselines*
  5. *Key Findings & Empirical Results*
  6. *Theoretical & Practical Contributions*
  7. *Documented Limitations & Constraints*
  8. *Future Research Directions*
  9. *Critical Academic Synthesis*

### ⚖️ Multi-Paper Comparative Analysis
- Select two or more uploaded papers to perform a rigorous comparative matrix analysis.
- Compares papers across 9 standardized dimensions: Research Objectives, Theoretical Foundations, Architectures, Datasets, Metrics, Computational Complexity, Novel Discoveries, Limitations, and Practical Applicability.
- Produces a side-by-side formatted Markdown synthesis table highlighting trade-offs and consensus.

### 🔍 Research Gap & Limitation Detection
- Analyzes author-stated constraints against cross-paper inferred gaps across 6 dimensions:
  - *Methodological & Architectural Limitations*
  - *Dataset, Benchmark & Evaluation Scope Gaps*
  - *Scalability, Latency & Resource Constraints*
  - *Conflicting Results & Unresolved Questions*
  - *Under-Explored Application Domains*
  - *Prioritized Future Research Agenda*
- Uses cautious academic phrasing to distinguish author-stated limitations from cross-paper inferences.

### 📌 Citation and Source References
- Every factual claim in research responses contains inline numerical brackets (`[1]`, `[2]`).
- A post-processing citation engine normalizes bracket formats, strips hallucinated citation numbers, and connects them to an interactive **Sources** expander.
- Each cited source displays the exact filename, 1-indexed page number, and verbatim text snippet.

### 📥 Publication-Ready Report Export (PDF & DOCX)
- 1-click export of any research response, summary, comparative matrix, or literature review:
  - **Academic PDF**: Generated via ReportLab Platypus, styled with formal typography, metadata header, executive summary, structured tables, and a complete reference bibliography.
  - **Word DOCX**: Generated via `python-docx` with native Word styles, shaded callouts, formatted tables, and bibliography.

### 🤖 Dual-Provider LLM Intelligence with Auto-Fallback
- **Primary Provider**: Google Gemini API (`gemini-2.5-flash`, `gemini-2.5-pro`, `gemini-1.5-pro`).
- **Secondary Provider**: Groq Cloud API (`qwen/qwen3.8-27b`, `openai/gpt-oss-120b`, `openai/gpt-oss-20b`).
- **Automatic Quota Failover**: If Gemini returns an HTTP 429 quota exhaustion or connection error, MSRA instantly retries the query using Groq (or vice-versa) with zero user intervention.

### 🛡️ Session Privacy & Dynamic Data Wipe
- Each browser session receives an isolated UUID workspace (`data/sessions/<uuid>/`) containing its private vectorstore and upload cache.
- Clicking **"Clear All Data"** safely cleans and releases all SQLite locks and files immediately.

---

## 3. System Architecture

MSRA follows a modular pipeline architecture where ingestion, vector indexing, retrieval, multi-provider inference, citation verification, and export are decoupled into independent layers:

```mermaid
flowchart TD
    User([User / Researcher]) -->|Uploads PDF 1..5| Ingestion[PDF Ingestion Layer<br/>pypdf & validate_pdf_file]
    User -->|Submits Research Query| Condense[Query Condensation<br/>Contextual Rewriting]

    subgraph INGESTION_PIPELINE [" Ingestion & Vectorization Pipeline "]
        Ingestion --> Extraction[Text Extraction & Page Metadata<br/>source, page, page_label]
        Extraction --> Chunking[Pure-Python Recursive Chunking<br/>size=1000, overlap=150]
        Chunking --> Embeddings[Sentence-Transformers Embeddings<br/>all-MiniLM-L6-v2]
        Embeddings --> Chroma[(ChromaDB Vectorstore<br/>Isolated per session)]
    end

    subgraph RETRIEVAL_REASONING [" Retrieval & Grounded Reasoning "]
        Condense --> Retriever[MMR & Similarity Search<br/>k=8 candidates]
        Chroma -.->|Relevant Chunks| Retriever
        Retriever --> PromptEngine[Academic Prompt Engine<br/>src/prompts.py]
        PromptEngine --> LLMGateway{LLM Gateway<br/>src/llm.py}

        LLMGateway -->|Primary Provider| Gemini[Google Gemini REST API]
        LLMGateway -->|Auto-Fallback on 429| Groq[Groq Cloud REST API]

        Gemini --> RawAnswer[Raw Response]
        Groq --> RawAnswer
    end

    subgraph VERIFICATION_EXPORT [" Verification & Export Layer "]
        RawAnswer --> CitationEngine[Citation Engine<br/>src/citations.py]
        CitationEngine --> GroundedResponse[Grounded Response with Citations [n]]
        GroundedResponse --> SourcesPanel[Interactive Sources Inspector<br/>File, Page, Snippet]
        GroundedResponse --> ExportEngine[Academic Export Engine<br/>src/export.py]
        ExportEngine --> PDFDoc[Publication PDF ReportLab]
        ExportEngine --> WordDoc[Formatted Word DOCX]
    end

    GroundedResponse --> UI[Streamlit Research Workspace<br/>app.py + 3D Particle Canvas]
    SourcesPanel --> UI
```

### How the 4 Research Features Use the Pipeline:
- **Summarization**: Queries all chunks belonging to a single target document, structuring content into 9 standardized academic sections.
- **Comparison**: Ingests chunks across 2+ selected documents, generating a multi-dimensional comparative matrix.
- **Gap Detection**: Directs MMR retrieval to extract limitations, boundary conditions, and future-work sections across the corpus.
- **Export Engine**: Takes verified Markdown text, parsed tables, and citation dictionaries to render publication-ready PDF and DOCX reports.

---

## 4. Technologies Used

Only technologies actually present in the source code are included:

| Category | Technology | Version | Purpose in MSRA |
|---|---|---|---|
| **Programming Language** | Python | `3.11` / `3.12` | Core application and RAG runtime |
| **Web UI Framework** | Streamlit | `>=1.35.0` | Interactive research workspace and state management |
| **UI Aesthetics** | Three.js | `r128` | WebGL 3D animated particle canvas background |
| **PDF Extraction** | pypdf | `>=4.2.0` | Fast text extraction, page parsing, and integrity validation |
| **RAG Orchestration** | LangChain / LangChain-Core | `>=0.2.0` | Document primitives and prompt template abstractions |
| **Vector Database** | ChromaDB | `>=0.5.0` | Per-session persistent vector index and metadata filtering |
| **Vector Integration** | langchain-chroma | `>=0.1.1` | LangChain wrapper for ChromaDB collections |
| **Dense Embeddings** | sentence-transformers | `>=3.0.0` | `all-MiniLM-L6-v2` (384-dimensional dense semantic vectors) |
| **Embedding Integration** | langchain-huggingface | `>=0.0.3` | Hugging Face embedding bridge for LangChain |
| **LLM Gateway (Gemini)** | Google Gemini API | REST | Direct REST integration for `gemini-2.5-flash` |
| **LLM Gateway (Groq)** | Groq Cloud API | REST | OpenAI-compatible REST integration for `qwen/qwen3.8-27b` |
| **HTTP Networking** | requests | `>=2.32.0` | Lightweight REST API calls without heavy vendor SDKs |
| **Environment Config** | python-dotenv | `>=1.0.1` | Local `.env` file secrets loading |
| **PDF Export Engine** | ReportLab | `>=4.2.0` | Publication-quality PDF reports with tables and bibliography |
| **DOCX Export Engine** | python-docx | `>=1.1.0` | Native Microsoft Word document generation |
| **Testing Framework** | pytest | `>=8.0.0` | Test runner for the 100-test automated verification suite |

---

## 5. Project Folder Structure

The project directory is organized into clean, dedicated modules:

```
MSRA Project/
├── app.py                      # Main Streamlit web application & UI orchestrator
├── config.py                   # System configuration, limits, timeouts & status constants
├── requirements.txt            # Production runtime dependencies
├── requirements-dev.txt        # Development & test suite dependencies (includes pytest)
├── pytest.ini                  # Pytest configuration & test discovery settings
├── .env.example                # Template for environment variables (GEMINI & GROQ keys)
├── .gitignore                  # Git exclusion rules for secrets, caches & databases
├── README.md                   # Complete system documentation
├── background_3d.py            # Backward-compatible proxy to src.background_3d
│
├── src/                        # Core Application Source Code
│   ├── __init__.py             # Package marker
│   ├── background_3d.py        # Three.js 3D WebGL particle background & custom CSS
│   ├── chain.py                # RAG reasoning, research Q&A & 4 research feature pipelines
│   ├── citations.py            # Citation bracket normalization, deduplication & sources
│   ├── export.py               # Academic PDF (ReportLab) and DOCX (python-docx) generator
│   ├── llm.py                  # Multi-provider LLM gateway (Gemini/Groq) with auto-fallback
│   ├── pdf_rag.py              # PDF parsing, pure-Python chunking & ChromaDB management
│   ├── prompts.py              # Academic system prompts with safe parameter formatting
│   └── workflows.py            # Guided research workflows (Compare, Gaps, Review)
│
├── utils/                      # Production Utilities & Isolation Layer
│   ├── __init__.py             # Package exports (validate_pdf_file, session helpers)
│   ├── errors.py               # PDF integrity checks, password detection & safe logging
│   ├── session.py              # Session UUID isolation, directory management & rate limits
│   └── citations.py            # Citation utility re-exports for backwards compatibility
│
├── docs/                       # Specifications & Academic Documentation
│   ├── PRD.md                  # Detailed Product Requirements Document & Handoff
│   └── PROJECT_SPEC.md         # Architecture specification & pipeline workflow diagram
│
├── data/                       # Storage & Benchmark Corpora
│   ├── uploads/                # Curated benchmark research papers (sample documents)
│   └── sessions/               # Isolated per-session SQLite databases & vector stores
│       └── .gitkeep            # Tracks directory structure while ignoring sessions
│
├── tests/                      # Automated Verification & Test Suites (100 Tests)
│   ├── conftest.py             # Global pytest fixtures and fast deterministic embeddings
│   ├── test_citations.py       # Bracket normalization & source mapping tests
│   ├── test_dom_ui_elements.py # Headless DOM & UI interaction tests
│   ├── test_four_research_features.py # Unit tests for Summarize, Compare, Gaps, Export
│   ├── test_full_system_lifecycle.py  # End-to-end full system lifecycle validation
│   ├── test_phase8_exports.py  # Automated PDF & DOCX export generation tests
│   ├── test_runtime_flows.py   # Runtime integration, deletion & fallback tests
│   ├── test_ui_apptest.py      # Streamlit AppTest framework simulation tests
│   └── doom/                   # Extreme Resilience & Stress Testing Suite (10 files)
│       ├── test_doom_bad_files.py        # Corrupted, encrypted, empty, and huge PDFs
│       ├── test_doom_citations.py        # Malformed, hallucinated, and unicode citations
│       ├── test_doom_concurrency.py      # Multi-session concurrency & directory locks
│       ├── test_doom_export.py           # Extreme table sizes and export stress tests
│       ├── test_doom_failure_injection.py # Simulated API 429 quotas and network drops
│       ├── test_doom_hostile_content.py  # Prompt injection and adversarial text handling
│       ├── test_doom_hostile_questions.py# Boundary inputs and rate limit enforcement
│       ├── test_doom_lifecycle.py        # Vector deletion, memory leaks & session wipe
│       └── test_doom_secrets.py          # API key sanitization and log leak prevention
│
└── eval/                       # Benchmark, Evaluation & Profiling Tools
    ├── profile_upload.py       # Millisecond-accurate pipeline performance profiler
    ├── run_eval.py             # 5-query academic benchmark against reference volume
    ├── eval_live_rag.py        # Interactive CLI evaluation of research Q&A
    ├── eval_qa_quality.py      # Multi-turn conversational quality benchmark
    └── diagnostics/            # Low-level API diagnostics
        ├── __init__.py         # Package marker
        ├── api_check_gemini.py # Direct Google Gemini REST API diagnostic probe
        └── api_check_models.py # Gemini model discovery & capability listing
```

---

## 6. Installation Instructions

Follow these step-by-step instructions in **Windows PowerShell**:

### Step 1: Clone the Repository
```powershell
git clone https://github.com/your-username/msra-project.git
cd "msra-project"
```

### 3. Create a Virtual Environment

```bash
python -m venv .myenv
```

Activate it on Windows:

```bash
.myenv\Scripts\activate
```

### 4. Install Dependencies

```bash
pip install -r requirements.txt
```
To also install testing tools (`pytest`):
```powershell
pip install -r requirements-dev.txt
```

### Step 5: Configure Environment Variables
Create your local `.env` configuration file by copying the template:
```powershell
Copy-Item .env.example .env
```
Open `.env` in any text editor and fill in your API keys (see next section).

---

## 7. Environment Variables

MSRA requires at least one LLM API key to function. Configuring both enables seamless zero-downtime automatic failover.

Open `.env` and configure:
```env
# Google Gemini API Key (from https://aistudio.google.com/)
GEMINI_API_KEY=your_gemini_api_key_here

# Groq Cloud API Key (from https://console.groq.com/)
GROQ_API_KEY=your_groq_api_key_here
```

> [!IMPORTANT]
> - Users must obtain their own API keys from [Google AI Studio](https://aistudio.google.com/) and [Groq Console](https://console.groq.com/). Both platforms offer free-tier access.
> - **Never commit real API keys to Git.** The `.gitignore` file is pre-configured to strictly exclude `.env` and `.env.*`.
> - For **Streamlit Community Cloud** deployment, enter keys under **App Settings → Secrets** (see [Deployment](#10-deployment-options)).

---

## 8. Running the Application

Ensure your virtual environment is active, then launch the Streamlit workspace:

```powershell
python -m streamlit run app.py
```
*(Or simply `streamlit run app.py`).*

Once launched, access the application in your browser:
- **Local Address**: `http://localhost:8501`
- **Network Address**: `http://<your-ip>:8501` *(accessible to devices on the same Wi-Fi)*

---

## 9. Running Automated Tests

MSRA includes an exhaustive automated verification suite of **100 tests** covering every component from unit logic to headless UI interactions and adversarial stress tests.

### Run All Tests
```powershell
pytest
```

### Run Tests with Verbose Output
```powershell
pytest -v
```

### Run Specific Test Suites
```powershell
# Run the DOOM Extreme Resilience & Stress Testing Suite (38 tests)
pytest tests/doom/ -v

# Run the UI DOM Interaction & Streamlit AppTest Suite
pytest tests/test_dom_ui_elements.py tests/test_ui_apptest.py -v

# Run the 4 Research Features & Lifecycle Test Suite
pytest tests/test_four_research_features.py tests/test_full_system_lifecycle.py -v

# Run the Citation Normalization Suite
pytest tests/test_citations.py -v

# Run the Export Generation Suite (PDF & DOCX)
pytest tests/test_phase8_exports.py -v
```

### Test Suite Categories:
- **Unit & Logic Tests** (`test_citations.py`, `test_four_research_features.py`): Validates bracket cleaning, citation normalization, snippet generation, and structured prompts.
- **UI & DOM Interaction Tests** (`test_dom_ui_elements.py`, `test_ui_apptest.py`): Simulates headless Streamlit runs, pill clicks, model selector changes, and empty states using `streamlit.testing.v1.AppTest`.
- **System Lifecycle Tests** (`test_full_system_lifecycle.py`, `test_runtime_flows.py`): Tests multi-paper upload, vector creation, paper deletion, rate limiting, and cache cleanup.
- **DOOM Resilience Suite** (`tests/doom/`): Stress tests malicious inputs, corrupted/encrypted/huge PDFs, simulated API HTTP 429 quota spikes, directory lock contention, and secret leakage prevention.

---

## 10. Deployment Options

### Option A: Streamlit Community Cloud (Recommended)
1. Push your project to a GitHub repository (ensure `.env` is ignored).
2. Sign in to [share.streamlit.io](https://share.streamlit.io/) with GitHub.
3. Click **Create App** and select your repository, branch (`main`), and main file (`app.py`).
4. Click **Advanced settings...** → **Secrets**, and paste your keys in TOML format:
   ```toml
   GEMINI_API_KEY = "your_actual_gemini_key"
   GROQ_API_KEY = "your_actual_groq_key"
   ```
5. Click **Deploy**. Streamlit will automatically install dependencies from `requirements.txt` and launch the app with a permanent public HTTPS URL.

### Option B: Local Network Sharing (Instant)
While running locally via `streamlit run app.py`, any smartphone, tablet, or laptop on the same local Wi-Fi can access the application via `http://<your-computer-ip>:8501`.

### Option C: Temporary Public Web Tunneling
To share with external reviewers without deploying to the cloud:
```powershell
npx localtunnel --port 8501
```
This generates a temporary public HTTPS link (e.g. `https://msra-demo.loca.lt`) accessible from any browser worldwide.

---

## 11. Security and Data Privacy

- **Credential Isolation**: API keys are accessed via `config.get_api_key()` which checks `st.secrets` first, then local environment variables. Keys are never logged or exposed to the client.
- **Sanitized Logging**: All server-side error logging passes through `utils.errors.safe_log()` which actively scrubs bearer tokens, API keys, and sensitive paths.
- **Per-Session Workspace Isolation**: Uploaded files and Chroma collections are isolated in individual per-session UUID directories (`data/sessions/<uuid>/`). Sessions cannot view, query, or delete other sessions' data.
- **Zero Data Leakage in Git**: The pre-configured `.gitignore` prevents `.env`, runtime vector stores (`*.sqlite3`, `*.bin`), and temporary session directories from ever being committed to GitHub.
- **Complete Client Data Erasure**: The **"Clear All Data"** button immediately deletes the session's temporary upload directory, resets the Chroma index, and clears Streamlit state.

---

## 12. System Limitations

- **Text-Layer Dependency (No Built-in OCR)**: MSRA relies on `pypdf` to extract digital text. Scanned document images or photographic PDFs lacking an embedded text layer cannot be indexed without prior OCR preprocessing.
- **Cold-Start Embedding Latency**: The `sentence-transformers/all-MiniLM-L6-v2` model runs locally on the CPU by default. The initial load takes ~15–30 seconds to initialize into RAM, after which embeddings are cached and run in sub-second batches.
- **Session Scale Constraints**: To preserve browser responsiveness and prevent memory exhaustion on shared hosting, sessions are configured with a maximum of 5 PDFs, 25 MB per file, and 300 total pages.
- **Free-Tier API Rate Limits**: Free-tier API keys on Google Gemini and Groq have requests-per-minute (RPM) limits. While MSRA automatically fails over between providers, exceeding quotas on both simultaneously will result in a graceful service notification.

---

## 13. Future Scope

The following enhancements are proposed for future development milestones:
- [ ] **OCR Pipeline Integration**: Incorporate an OCR preprocessing engine (e.g., Tesseract or Surya) for scanned historical papers and photographic documents.
- [ ] **Hybrid Dense + Sparse Search**: Integrate BM25 keyword matching with Chroma dense vector similarity for improved acronym and exact-symbol retrieval.
- [ ] **BibTeX Citation Export**: Add one-click export of structured `.bib` reference citations alongside PDF and DOCX reports.
- [ ] **Persistent User Accounts**: Optional database-backed user authentication to allow saving and revisiting multi-paper research projects across sessions.
- [ ] **Local Offline LLM Support**: Support local quantized GGUF models via `llama.cpp` for fully offline, air-gapped institutional deployments.

---

## 14. Author & Project Information

| Field | Details |
|---|---|
| **Project Name** | **MSRA – Modular Smart Research Assistant** |
| **Academic Institution** | **Sant Baba Bhag Singh University (SBBSU)** |
| **Department** | `[Your Department / Faculty, e.g., Department of Computer Science & Engineering]` |
| **Student / Author Name** | `[Your Name]` |
| **Registration / Roll No.** | `[Your Roll / Registration Number]` |
| **Project Guide / Supervisor** | `[Supervisor Name / Faculty Advisor]` |
| **Contact Email** | `[Your Email Address]` |
| **GitHub Repository** | `[Your GitHub Repository Link]` |

---

### Academic Integrity & License
This project was developed for academic, research, and educational purposes. Distributed under the **MIT License**. Built with Streamlit, LangChain, Hugging Face, ChromaDB, and ReportLab.
