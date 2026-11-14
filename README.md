# MSRA – Modular Smart Research Assistant

An AI-powered research assistant designed to help students and researchers understand academic documents, retrieve relevant information, and generate structured research insights using Large Language Models (LLMs) and Retrieval-Augmented Generation (RAG).

## Project Overview

MSRA (Modular Smart Research Assistant) is a Python-based research assistant that allows users to upload research papers and PDF documents, ask questions, generate summaries, compare multiple papers, and identify potential research gaps.

The system uses document processing, semantic search, vector embeddings, and LLM-based reasoning to provide context-aware answers supported by source references.

## Key Features

- **PDF Question Answering:** Ask questions about uploaded research documents.
- **Multi-PDF Research:** Upload and analyze multiple research papers together.
- **Citation Engine:** Generate source-based answers with document and page references.
- **Research Summarization:** Generate structured summaries of academic papers.
- **Paper Comparison:** Compare multiple research papers based on their content.
- **Literature Review:** Generate organized literature review insights.
- **Research Gap Detection:** Identify limitations and potential research gaps.
- **Document Export:** Export research outputs into PDF and DOCX formats.
- **LLM Provider Support:** Support multiple LLM providers with model selection and fallback handling.

## Technology Stack

| Category | Technologies |
|---|---|
| Programming Language | Python |
| Frontend | Streamlit |
| AI Framework | LangChain |
| Language Models | Gemini, Groq |
| Embeddings | Hugging Face |
| Embedding Model | all-MiniLM-L6-v2 |
| Vector Database | ChromaDB |
| PDF Processing | PyPDFLoader |
| Document Splitting | RecursiveCharacterTextSplitter |
| Testing | Pytest |

## How It Works

1. User uploads one or more research papers in PDF format.
2. The system extracts text from the documents.
3. Documents are divided into smaller chunks.
4. Hugging Face embeddings convert text chunks into vectors.
5. ChromaDB stores the document vectors.
6. Relevant information is retrieved using semantic search.
7. The selected LLM generates answers using the retrieved context.
8. The Citation Engine provides supporting source and page references.

## Project Structure

```text
MSRA/
│
├── app.py
├── config.py
├── background_3d.py
│
├── src/
│   ├── chain.py
│   ├── citations.py
│   ├── export.py
│   ├── llm.py
│   ├── pdf_rag.py
│   ├── prompts.py
│   └── workflows.py
│
├── utils/
├── tests/
├── eval/
├── docs/
│
├── requirements.txt
├── requirements-dev.txt
├── pytest.ini
└── README.md
```

## Installation and Setup

### 1. Clone the Repository

```bash
git clone https://github.com/nangluanmol28-art/MSRA-Modular-Smart-Research-Assistant.git
```

### 2. Navigate to the Project

```bash
cd MSRA-Modular-Smart-Research-Assistant
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

### 5. Configure API Credentials

Configure the required LLM provider API credentials using the configuration instructions in the project.

Keep all API keys private. Never upload actual secrets to GitHub.

### 6. Run the Application

```bash
streamlit run app.py
```

## Testing

Run the project's test suite using:

```bash
pytest
```

## Project Objective

The main objective of MSRA is to simplify academic research by combining document retrieval, AI-powered question answering, citation generation, and research analysis in a single modular application.

## Future Scope

- Improved retrieval accuracy.
- Support for additional document formats.
- Enhanced research evaluation.
- More LLM provider integrations.
- Advanced academic research workflows.

## Author

**Anmol Singh**

B.Tech – Computer Science and Engineering (AI & ML)

Sant Baba Bhag Singh University

---

**MSRA – Modular Smart Research Assistant**

*Making academic research smarter, faster, and more organized.*
