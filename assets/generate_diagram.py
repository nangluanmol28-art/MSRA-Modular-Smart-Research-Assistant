"""
MSRA Architecture Diagram Generator
====================================
Generates a crisp, high-resolution (2400x1460) system architecture diagram for
MSRA – Modular Smart Research Assistant in modern dark navy and teal styling.
"""

import os
from PIL import Image, ImageDraw, ImageFont

os.makedirs('assets', exist_ok=True)
out_path = os.path.join('assets', 'architecture.png')

W, H = 2400, 1460
img = Image.new('RGB', (W, H), '#070c18')
draw = ImageDraw.Draw(img)

# --- 1. Background Grid ---
grid_color = '#0d1829'
for x in range(0, W, 40):
    draw.line([(x, 0), (x, H)], fill=grid_color, width=1)
for y in range(0, H, 40):
    draw.line([(0, y), (W, y)], fill=grid_color, width=1)

# --- Fonts ---
def get_font(name, size):
    path = os.path.join(r'C:\Windows\Fonts', name)
    return ImageFont.truetype(path, size)

f_title = get_font('segoeuib.ttf', 38)
f_subtitle = get_font('segoeui.ttf', 17)
f_pill = get_font('segoeuib.ttf', 12)
f_col_hdr = get_font('segoeuib.ttf', 18)
f_card_hdr = get_font('segoeuib.ttf', 18)
f_badge = get_font('consola.ttf', 12)
f_body = get_font('segoeui.ttf', 13)
f_body_bold = get_font('segoeuib.ttf', 13)
f_arrow = get_font('segoeuib.ttf', 11)

# --- Color Palette ---
BG_NAVY = '#070c18'
CONTAINER_BG = '#0a1324'
CONTAINER_BORDER = '#1b2d4b'

CARD_BG = '#0e1a32'
CARD_BORDER = '#1d3356'
TEAL_MAIN = '#14b8a6'
TEAL_GLOW = '#2dd4bf'
CYAN_MAIN = '#06b6d4'
CYAN_BRIGHT = '#38bdf8'
BLUE_ACCENT = '#3b82f6'
PURPLE_ACCENT = '#8b5cf6'
EMERALD_ACCENT = '#10b981'

TEXT_WHITE = '#ffffff'
TEXT_LIGHT = '#e2e8f0'
TEXT_MUTED = '#94a3b8'
TEXT_DARK = '#64748b'

# --- Drawing Helpers ---
def draw_rounded_card(x, y, w, h, radius=12, fill=CARD_BG, border=CARD_BORDER, border_width=2, top_accent=None):
    # Shadow offset
    draw.rounded_rectangle([x + 3, y + 3, x + w + 3, y + h + 3], radius=radius, fill='#040810')
    draw.rounded_rectangle([x, y, x + w, y + h], radius=radius, fill=fill, outline=border, width=border_width)
    if top_accent:
        draw.rounded_rectangle([x, y, x + w, y + 6], radius=radius, fill=top_accent)
        draw.rectangle([x, y + 4, x + w, y + 8], fill=top_accent)

def draw_pill(x, y, text, bg_color='#132d46', text_color='#2dd4bf', border_color='#14b8a6'):
    bbox = f_pill.getbbox(text)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    pw = tw + 20
    ph = th + 10
    draw.rounded_rectangle([x, y, x + pw, y + ph], radius=ph // 2, fill=bg_color, outline=border_color, width=1)
    draw.text((x + 10, y + 4), text, font=f_pill, fill=text_color)
    return pw, ph

def draw_arrow_v(x1, y1, x2, y2, label='', color='#14b8a6', width=3, direction='down'):
    draw.line([(x1, y1), (x2, y2)], fill=color, width=width)
    ah = 9
    if direction == 'down':
        draw.polygon([(x2, y2), (x2 - ah // 2, y2 - ah), (x2 + ah // 2, y2 - ah)], fill=color)
    else:
        draw.polygon([(x2, y2), (x2 - ah // 2, y2 + ah), (x2 + ah // 2, y2 + ah)], fill=color)
    if label:
        bbox = f_arrow.getbbox(label)
        lw = bbox[2] - bbox[0] + 16
        lh = bbox[3] - bbox[1] + 8
        mx = (x1 + x2) // 2
        my = (y1 + y2) // 2
        draw.rounded_rectangle([mx - lw // 2, my - lh // 2, mx + lw // 2, my + lh // 2], radius=4, fill='#071828', outline=color, width=1)
        draw.text((mx - lw // 2 + 8, my - lh // 2 + 3), label, font=f_arrow, fill='#e2e8f0')

def draw_arrow_orthogonal(points, label='', color='#14b8a6', width=3, arrow_dir='down'):
    for i in range(len(points) - 1):
        draw.line([points[i], points[i + 1]], fill=color, width=width)
    last = points[-1]
    ah = 9
    if arrow_dir == 'down':
        draw.polygon([(last[0], last[1]), (last[0] - ah // 2, last[1] - ah), (last[0] + ah // 2, last[1] - ah)], fill=color)
    elif arrow_dir == 'up':
        draw.polygon([(last[0], last[1]), (last[0] - ah // 2, last[1] + ah), (last[0] + ah // 2, last[1] + ah)], fill=color)
    elif arrow_dir == 'right':
        draw.polygon([(last[0], last[1]), (last[0] - ah, last[1] - ah // 2), (last[0] - ah, last[1] + ah // 2)], fill=color)
    elif arrow_dir == 'left':
        draw.polygon([(last[0], last[1]), (last[0] + ah, last[1] - ah // 2), (last[0] + ah, last[1] + ah // 2)], fill=color)
    if label:
        p1, p2 = points[0], points[1]
        mx = (p1[0] + p2[0]) // 2
        my = (p1[1] + p2[1]) // 2
        bbox = f_arrow.getbbox(label)
        lw = bbox[2] - bbox[0] + 16
        lh = bbox[3] - bbox[1] + 8
        draw.rounded_rectangle([mx - lw // 2, my - lh // 2, mx + lw // 2, my + lh // 2], radius=4, fill='#071828', outline=color, width=1)
        draw.text((mx - lw // 2 + 8, my - lh // 2 + 3), label, font=f_arrow, fill='#e2e8f0')

# ==============================================================================
# 2. HEADER
# ==============================================================================
draw_pill(80, 35, 'SYSTEM ARCHITECTURE & TECHNICAL DATA FLOW', bg_color='#0b2238', text_color='#2dd4bf', border_color='#14b8a6')
draw.text((80, 72), 'MSRA – Modular Smart Research Assistant', font=f_title, fill=TEXT_WHITE)
draw.text((80, 122), 'End-to-End PDF RAG Workflow: Multi-Document Ingestion, ChromaDB Indexing, Dual LLM Gateway & Grounded Citations', font=f_subtitle, fill=TEXT_MUTED)

# ==============================================================================
# 3. TIER 1: STREAMLIT USER INTERFACE (Full Width Container)
# ==============================================================================
ui_box_x = 70
ui_box_y = 165
ui_box_w = 2260
ui_box_h = 245
draw.rounded_rectangle([ui_box_x, ui_box_y, ui_box_x + ui_box_w, ui_box_y + ui_box_h], radius=16, fill=CONTAINER_BG, outline=CONTAINER_BORDER, width=2)
draw.text((ui_box_x + 30, ui_box_y + 16), 'STREAMLIT PRESENTATION & WORKSPACE LAYER (app.py + src/background_3d.py)', font=f_col_hdr, fill=CYAN_BRIGHT)

# UI Card 1: PDF Upload & Paper Manager
c1_x = 100
c1_y = 210
c1_w = 520
c1_h = 180
draw_rounded_card(c1_x, c1_y, c1_w, c1_h, top_accent=TEAL_MAIN)
draw.text((c1_x + 20, c1_y + 18), 'PDF Upload & Paper Manager', font=f_card_hdr, fill=TEXT_WHITE)
draw.text((c1_x + 20, c1_y + 44), 'Sidebar Controls & Multi-Document Registry', font=f_badge, fill=TEAL_GLOW)
draw.text((c1_x + 20, c1_y + 72), '• Multi-PDF Upload (Max 5 PDFs, 25MB each, max 300 pages)', font=f_body, fill=TEXT_LIGHT)
draw.text((c1_x + 20, c1_y + 94), '• Pre-Ingestion Validation: PDF integrity, corruption, empty check', font=f_body, fill=TEXT_LIGHT)
draw.text((c1_x + 20, c1_y + 116), '• Document Metadata: Name, 1-indexed pages, chunk count, size', font=f_body, fill=TEXT_LIGHT)
draw.text((c1_x + 20, c1_y + 138), '• 1-Click Document Removal & Full Session Data Erasure', font=f_body, fill=TEXT_LIGHT)

# UI Card 2: Research Q&A Chat Interface
c2_x = 660
c2_y = 210
c2_w = 520
c2_h = 180
draw_rounded_card(c2_x, c2_y, c2_w, c2_h, top_accent=CYAN_MAIN)
draw.text((c2_x + 20, c2_y + 18), 'Research Q&A Chat Workspace', font=f_card_hdr, fill=TEXT_WHITE)
draw.text((c2_x + 20, c2_y + 44), 'Conversational Retrieval & Query Condensation', font=f_badge, fill=CYAN_BRIGHT)
draw.text((c2_x + 20, c2_y + 72), '• Natural language question input across indexed papers', font=f_body, fill=TEXT_LIGHT)
draw.text((c2_x + 20, c2_y + 94), '• Standalone query condensation with multi-turn chat history', font=f_body, fill=TEXT_LIGHT)
draw.text((c2_x + 20, c2_y + 116), '• Grounded streaming responses with inline citations [1], [2]', font=f_body, fill=TEXT_LIGHT)
draw.text((c2_x + 20, c2_y + 138), '• Interactive Sources Inspector: filenames, pages, verbatim snippets', font=f_body, fill=TEXT_LIGHT)

# UI Card 3: 4 Dedicated Research Tools
c3_x = 1220
c3_y = 210
c3_w = 520
c3_h = 180
draw_rounded_card(c3_x, c3_y, c3_w, c3_h, top_accent=PURPLE_ACCENT)
draw.text((c3_x + 20, c3_y + 18), '4 Dedicated Research Tools', font=f_card_hdr, fill=TEXT_WHITE)
draw.text((c3_x + 20, c3_y + 44), 'Right-Hand Workspace Research Analytical Suite', font=f_badge, fill='#c084fc')
draw.text((c3_x + 20, c3_y + 72), '1. Paper Summarization: 9 structured academic dimensions', font=f_body, fill=TEXT_LIGHT)
draw.text((c3_x + 20, c3_y + 94), '2. Multi-Paper Comparison: 9-dimension cross-paper matrix', font=f_body, fill=TEXT_LIGHT)
draw.text((c3_x + 20, c3_y + 116), '3. Research Gap Detection: Author-stated vs. inferred limits', font=f_body, fill=TEXT_LIGHT)
draw.text((c3_x + 20, c3_y + 138), '4. Literature Review Generator: Thematic corpus synthesis', font=f_body, fill=TEXT_LIGHT)

# UI Card 4: Academic Export Engine
c4_x = 1780
c4_y = 210
c4_w = 520
c4_h = 180
draw_rounded_card(c4_x, c4_y, c4_w, c4_h, top_accent=EMERALD_ACCENT)
draw.text((c4_x + 20, c4_y + 18), 'Academic Publication Export', font=f_card_hdr, fill=TEXT_WHITE)
draw.text((c4_x + 20, c4_y + 44), 'ReportLab Platypus & python-docx Generators', font=f_badge, fill='#6ee7b7')
draw.text((c4_x + 20, c4_y + 72), '• Formal PDF Export: Custom headers, metadata, typography', font=f_body, fill=TEXT_LIGHT)
draw.text((c4_x + 20, c4_y + 94), '• Word DOCX Export: Native Word styles & formatted callouts', font=f_body, fill=TEXT_LIGHT)
draw.text((c4_x + 20, c4_y + 116), '• Markdown table conversion with custom cell auto-wrap', font=f_body, fill=TEXT_LIGHT)
draw.text((c4_x + 20, c4_y + 138), '• Consolidated Bibliography: Deduplicated reference appendix', font=f_body, fill=TEXT_LIGHT)

# ==============================================================================
# 4. LOWER TIERS: 3 COLUMNS OF THE PIPELINE
# ==============================================================================

# ----------------- COLUMN 1: INGESTION & VECTOR PIPELINE -----------------
col1_x = 70
col1_y = 445
col1_w = 720
col1_h = 920
draw.rounded_rectangle([col1_x, col1_y, col1_x + col1_w, col1_y + col1_h], radius=16, fill=CONTAINER_BG, outline=CONTAINER_BORDER, width=2)
draw.text((col1_x + 30, col1_y + 20), 'INGESTION & VECTORIZATION PIPELINE', font=f_col_hdr, fill=TEAL_GLOW)
draw.text((col1_x + 30, col1_y + 46), 'Document Loading, Pure-Python Chunking & Dense Embeddings', font=f_badge, fill=TEXT_MUTED)

# Box 1A: PDF Text Extraction
b1a_x = 100
b1a_y = 510
b1a_w = 660
b1a_h = 240
draw_rounded_card(b1a_x, b1a_y, b1a_w, b1a_h, top_accent=TEAL_MAIN)
draw.text((b1a_x + 24, b1a_y + 20), 'PDF Text Extraction (PyPDFLoader)', font=f_card_hdr, fill=TEXT_WHITE)
draw.text((b1a_x + 24, b1a_y + 48), 'Engine: pypdf.PdfReader / PyPDFLoader (src/pdf_rag.py)', font=f_badge, fill=TEAL_GLOW)
draw.text((b1a_x + 24, b1a_y + 80), '• Ingests PDF file bytes from Streamlit file uploader buffer', font=f_body, fill=TEXT_LIGHT)
draw.text((b1a_x + 24, b1a_y + 104), '• Extracts raw text layer page-by-page with whitespace preservation', font=f_body, fill=TEXT_LIGHT)
draw.text((b1a_x + 24, b1a_y + 128), '• Attaches provenance metadata: source filename, page index (0-indexed)', font=f_body, fill=TEXT_LIGHT)
draw.text((b1a_x + 24, b1a_y + 152), '• Normalizes human-facing 1-indexed page_label for citation accuracy', font=f_body, fill=TEXT_LIGHT)
draw.text((b1a_x + 24, b1a_y + 176), '• SHA-256 document hashing for deduplication & state tracking', font=f_body, fill=TEXT_LIGHT)
draw.text((b1a_x + 24, b1a_y + 200), '• Output: LangChain Document objects with intact page metadata', font=f_body, fill=CYAN_BRIGHT)

# Box 1B: Text Chunking
b1b_x = 100
b1b_y = 800
b1b_w = 660
b1b_h = 240
draw_rounded_card(b1b_x, b1b_y, b1b_w, b1b_h, top_accent=TEAL_MAIN)
draw.text((b1b_x + 24, b1b_y + 20), 'Text Chunking (RecursiveCharacterTextSplitter)', font=f_card_hdr, fill=TEXT_WHITE)
draw.text((b1b_x + 24, b1b_y + 48), 'Algorithm: Pure-Python Boundary-Aware Recursive Splitter', font=f_badge, fill=TEAL_GLOW)
draw.text((b1b_x + 24, b1b_y + 80), '• Splits on hierarchical boundaries: paragraph, newline, sentence, space', font=f_body, fill=TEXT_LIGHT)
draw.text((b1b_x + 24, b1b_y + 104), '• Chunk Size: 1000 characters (captures complete semantic thoughts)', font=f_body, fill=TEXT_LIGHT)
draw.text((b1b_x + 24, b1b_y + 128), '• Chunk Overlap: 150 characters (preserves cross-chunk context)', font=f_body, fill=TEXT_LIGHT)
draw.text((b1b_x + 24, b1b_y + 152), '• Injects sequential chunk_index and inherits parent page metadata', font=f_body, fill=TEXT_LIGHT)
draw.text((b1b_x + 24, b1b_y + 176), '• Fast pure-Python execution without heavy tokenizer overhead', font=f_body, fill=TEXT_LIGHT)
draw.text((b1b_x + 24, b1b_y + 200), '• Output: Standardized chunks with exact page & document provenance', font=f_body, fill=CYAN_BRIGHT)

# Box 1C: Embedding Generation
b1c_x = 100
b1c_y = 1090
b1c_w = 660
b1c_h = 240
draw_rounded_card(b1c_x, b1c_y, b1c_w, b1c_h, top_accent=TEAL_MAIN)
draw.text((b1c_x + 24, b1c_y + 20), 'Embedding Generation (HuggingFace)', font=f_card_hdr, fill=TEXT_WHITE)
draw.text((b1c_x + 24, b1c_y + 48), 'Model: sentence-transformers/all-MiniLM-L6-v2 (384 Dimensions)', font=f_badge, fill=TEAL_GLOW)
draw.text((b1c_x + 24, b1c_y + 80), '• Efficient transformer mapping text chunks into 384-dim vector space', font=f_body, fill=TEXT_LIGHT)
draw.text((b1c_x + 24, b1c_y + 104), '• Batch embedding execution (batch_size = 64) for high throughput', font=f_body, fill=TEXT_LIGHT)
draw.text((b1c_x + 24, b1c_y + 128), '• L2-normalized embeddings for fast cosine similarity computation', font=f_body, fill=TEXT_LIGHT)
draw.text((b1c_x + 24, b1c_y + 152), '• Cached in memory via @st.cache_resource (avoids redundant reloads)', font=f_body, fill=TEXT_LIGHT)
draw.text((b1c_x + 24, b1c_y + 176), '• Local safetensors weights cache (.cache/huggingface) prevents re-download', font=f_body, fill=TEXT_LIGHT)
draw.text((b1c_x + 24, b1c_y + 200), '• Output: Normalized 384-dimensional dense vectors + metadata', font=f_body, fill=CYAN_BRIGHT)

# ----------------- COLUMN 2: VECTOR STORAGE & RETRIEVAL -----------------
col2_x = 840
col2_y = 445
col2_w = 720
col2_h = 920
draw.rounded_rectangle([col2_x, col2_y, col2_x + col2_w, col2_y + col2_h], radius=16, fill=CONTAINER_BG, outline=CONTAINER_BORDER, width=2)
draw.text((col2_x + 30, col2_y + 20), 'VECTOR STORAGE & HYBRID RETRIEVAL', font=f_col_hdr, fill=CYAN_BRIGHT)
draw.text((col2_x + 30, col2_y + 46), 'Per-Session ChromaDB Isolation, MMR Search & Query Condensation', font=f_badge, fill=TEXT_MUTED)

# Box 2A: Vector Storage (ChromaDB)
b2a_x = 870
b2a_y = 510
b2a_w = 660
b2a_h = 380
draw_rounded_card(b2a_x, b2a_y, b2a_w, b2a_h, top_accent=CYAN_MAIN)
draw.text((b2a_x + 24, b2a_y + 20), 'Vector Storage (ChromaDB)', font=f_card_hdr, fill=TEXT_WHITE)
draw.text((b2a_x + 24, b2a_y + 48), 'Database: ChromaDB 0.5+ / langchain-chroma', font=f_badge, fill=CYAN_BRIGHT)
draw.text((b2a_x + 24, b2a_y + 82), '• Per-Session Dynamic UUID Storage: data/sessions/<uuid>/chroma', font=f_body, fill=TEXT_LIGHT)
draw.text((b2a_x + 24, b2a_y + 108), '• Complete Session Isolation: Zero cross-contamination between users', font=f_body, fill=TEXT_LIGHT)
draw.text((b2a_x + 24, b2a_y + 134), '• Persistent SQLite + HNSW index files for fast vector retrieval', font=f_body, fill=TEXT_LIGHT)
draw.text((b2a_x + 24, b2a_y + 160), '• Incremental Ingestion: Add new papers without rebuilding database', font=f_body, fill=TEXT_LIGHT)
draw.text((b2a_x + 24, b2a_y + 186), '• Targeted Deletion: Remove individual papers using source metadata filters', font=f_body, fill=TEXT_LIGHT)
draw.text((b2a_x + 24, b2a_y + 212), '• Metadata Filtering: Restricts searches to specific papers during compare', font=f_body, fill=TEXT_LIGHT)
draw.text((b2a_x + 24, b2a_y + 238), '• Windows-Safe File Locks: gc.collect() & retry routines prevent lockup', font=f_body, fill=TEXT_LIGHT)
draw.text((b2a_x + 24, b2a_y + 264), '• Auto-Cleanup: Expired sessions purged automatically after 2 hours', font=f_body, fill=TEXT_LIGHT)
draw.text((b2a_x + 24, b2a_y + 300), 'Collection Name: msra_<session_id_hash>', font=f_badge, fill='#7dd3fc')
draw.text((b2a_x + 24, b2a_y + 330), 'Persistence Path: data/sessions/<uuid>/chroma/chroma.sqlite3', font=f_badge, fill='#7dd3fc')

# Box 2B: MMR Retrieval Engine
b2b_x = 870
b2b_y = 940
b2b_w = 660
b2b_h = 390
draw_rounded_card(b2b_x, b2b_y, b2b_w, b2b_h, top_accent=CYAN_MAIN)
draw.text((b2b_x + 24, b2b_y + 20), 'MMR Retrieval (Maximal Marginal Relevance)', font=f_card_hdr, fill=TEXT_WHITE)
draw.text((b2b_x + 24, b2b_y + 48), 'Strategy: Balanced Semantic Similarity & Diversity (lambda_mult=0.7)', font=f_badge, fill=CYAN_BRIGHT)
draw.text((b2b_x + 24, b2b_y + 82), '• Conversational Query Condensation (src/chain.py):', font=f_body_bold, fill=TEXT_WHITE)
draw.text((b2b_x + 40, b2b_y + 106), 'Rewrites follow-up questions into standalone queries using history', font=f_body, fill=TEXT_LIGHT)
draw.text((b2b_x + 24, b2b_y + 134), '• Two-Stage MMR Candidate Ranking:', font=f_body_bold, fill=TEXT_WHITE)
draw.text((b2b_x + 40, b2b_y + 158), 'Stage 1: Fetch candidate pool of k=20 nearest neighbor chunks', font=f_body, fill=TEXT_LIGHT)
draw.text((b2b_x + 40, b2b_y + 182), 'Stage 2: Select top k=8 maximally distinct & non-redundant chunks', font=f_body, fill=TEXT_LIGHT)
draw.text((b2b_x + 24, b2b_y + 210), '• Eliminates near-duplicate passages from identical sections', font=f_body, fill=TEXT_LIGHT)
draw.text((b2b_x + 24, b2b_y + 236), '• Multi-Paper Fair Representation: Balances evidence across papers', font=f_body, fill=TEXT_LIGHT)
draw.text((b2b_x + 24, b2b_y + 262), '• Preserves chunk context and exact source/page metadata', font=f_body, fill=TEXT_LIGHT)
draw.text((b2b_x + 24, b2b_y + 296), 'Output: Exactly k=8 diverse, high-confidence evidence passages', font=f_badge, fill=TEAL_GLOW)
draw.text((b2b_x + 24, b2b_y + 326), 'Metadata Attached: {source, page, page_label, file_hash}', font=f_badge, fill=TEAL_GLOW)

# ----------------- COLUMN 3: REASONING, CITATIONS & EXPORT -----------------
col3_x = 1610
col3_y = 445
col3_w = 720
col3_h = 920
draw.rounded_rectangle([col3_x, col3_y, col3_x + col3_w, col3_y + col3_h], radius=16, fill=CONTAINER_BG, outline=CONTAINER_BORDER, width=2)
draw.text((col3_x + 30, col3_y + 20), 'REASONING, GROUNDING & CITATIONS', font=f_col_hdr, fill='#a78bfa')
draw.text((col3_x + 30, col3_y + 46), 'Dual-Provider LLMs, Grounding Prompt, Verification & Formatting', font=f_badge, fill=TEXT_MUTED)

# Box 3A: LLM Processing & Auto-Fallback
b3a_x = 1640
b3a_y = 510
b3a_w = 660
b3a_h = 240
draw_rounded_card(b3a_x, b3a_y, b3a_w, b3a_h, top_accent=PURPLE_ACCENT)
draw.text((b3a_x + 24, b3a_y + 20), 'LLM Processing (Gemini / Groq)', font=f_card_hdr, fill=TEXT_WHITE)
draw.text((b3a_x + 24, b3a_y + 48), 'Dual-Gateway REST API with Automatic Quota Failover', font=f_badge, fill='#c084fc')
draw.text((b3a_x + 24, b3a_y + 80), '• Primary: Google Gemini API (gemini-2.5-flash / gemini-2.5-pro)', font=f_body, fill=TEXT_LIGHT)
draw.text((b3a_x + 24, b3a_y + 104), '• Secondary: Groq Cloud API (qwen/qwen3.8-27b, openai/gpt-oss-120b)', font=f_body, fill=TEXT_LIGHT)
draw.text((b3a_x + 24, b3a_y + 128), '• Direct REST Implementation via requests (zero heavy vendor SDKs)', font=f_body, fill=TEXT_LIGHT)
draw.text((b3a_x + 24, b3a_y + 152), '• Automatic Failover: On HTTP 429 quota exhaustion or connection drop,', font=f_body, fill=TEXT_LIGHT)
draw.text((b3a_x + 40, b3a_y + 176), 'seamlessly retries with secondary provider in < 1 second', font=f_body_bold, fill='#c084fc')
draw.text((b3a_x + 24, b3a_y + 202), '• Supports token streaming for fast real-time user feedback', font=f_body, fill=TEXT_LIGHT)

# Box 3B: Response Generation
b3b_x = 1640
b3b_y = 800
b3b_w = 660
b3b_h = 240
draw_rounded_card(b3b_x, b3b_y, b3b_w, b3b_h, top_accent=PURPLE_ACCENT)
draw.text((b3b_x + 24, b3b_y + 20), 'Academic Response Generation', font=f_card_hdr, fill=TEXT_WHITE)
draw.text((b3b_x + 24, b3b_y + 48), 'Strict Grounding & Anti-Hallucination Prompt Architecture', font=f_badge, fill='#c084fc')
draw.text((b3b_x + 24, b3b_y + 80), '• Formatted Context: Chunks injected as [1] Paper.pdf (Page X): <text>', font=f_body, fill=TEXT_LIGHT)
draw.text((b3b_x + 24, b3b_y + 104), '• Grounding Mandate: Every factual claim must carry inline citation [n]', font=f_body, fill=TEXT_LIGHT)
draw.text((b3b_x + 24, b3b_y + 128), '• Refusal Policy: If retrieved text does not support the answer, states:', font=f_body, fill=TEXT_LIGHT)
draw.text((b3b_x + 40, b3b_y + 152), "'I couldn't find this in the uploaded papers.' (Zero hallucination)", font=f_body_bold, fill='#f43f5e')
draw.text((b3b_x + 24, b3b_y + 178), '• Specialized prompts for Summaries, Comparison Matrices & Research Gaps', font=f_body, fill=TEXT_LIGHT)
draw.text((b3b_x + 24, b3b_y + 202), '• Output: Academic structured answer with candidate inline citations', font=f_body, fill=CYAN_BRIGHT)

# Box 3C: Citation Engine
b3c_x = 1640
b3c_y = 1090
b3c_w = 660
b3c_h = 240
draw_rounded_card(b3c_x, b3c_y, b3c_w, b3c_h, top_accent=EMERALD_ACCENT)
draw.text((b3c_x + 24, b3c_y + 20), 'Citation Engine (Source IDs & Pages)', font=f_card_hdr, fill=TEXT_WHITE)
draw.text((b3c_x + 24, b3c_y + 48), 'Post-Processing Verification & Normalization (src/citations.py)', font=f_badge, fill='#6ee7b7')
draw.text((b3c_x + 24, b3c_y + 80), '• Bracket Normalization: Converts odd brackets 【1】 and (1) to [1]', font=f_body, fill=TEXT_LIGHT)
draw.text((b3c_x + 24, b3c_y + 104), '• Citation Verification: Strips hallucinated IDs not present in retrieved context', font=f_body, fill=TEXT_LIGHT)
draw.text((b3c_x + 24, b3c_y + 128), '• Source Dropdown Filtering: Keeps only sources actually cited in the text', font=f_body, fill=TEXT_LIGHT)
draw.text((b3c_x + 24, b3c_y + 152), '• Verbatim Snippet Extraction: Generates 150-char contextual excerpt', font=f_body, fill=TEXT_LIGHT)
draw.text((b3c_x + 24, b3c_y + 176), '• Deduplication: Collapses duplicate references to identical pages', font=f_body, fill=TEXT_LIGHT)
draw.text((b3c_x + 24, b3c_y + 202), '• Output: Verified Answer + Active Sources {id, source, page, snippet}', font=f_body, fill='#6ee7b7')

# ==============================================================================
# 5. DIRECTIONAL FLOW ARROWS
# ==============================================================================
ARROW_TEAL = '#14b8a6'
ARROW_CYAN = '#06b6d4'
ARROW_PURPLE = '#a855f7'
ARROW_GREEN = '#10b981'

# Flow 1: UI Upload Card -> PDF Text Extraction
draw_arrow_v(360, 390, 360, 508, label='PDF Byte Stream', color=ARROW_TEAL, direction='down')

# Flow 2: Extraction -> Chunking
draw_arrow_v(430, 750, 430, 798, label='Extracted Pages', color=ARROW_TEAL, direction='down')

# Flow 3: Chunking -> Embeddings
draw_arrow_v(430, 1040, 430, 1088, label='1000-char Text Chunks', color=ARROW_TEAL, direction='down')

# Flow 4: Embeddings -> ChromaDB
draw_arrow_orthogonal([
    (760, 1200),
    (810, 1200),
    (810, 700),
    (868, 700)
], label='384-dim Vectors', color=ARROW_TEAL, arrow_dir='right')

# Flow 5: UI Chat Workspace -> MMR Retrieval
draw_arrow_orthogonal([
    (920, 390),
    (920, 430),
    (830, 430),
    (830, 915),
    (1100, 915),
    (1100, 938)
], label='User Query', color=ARROW_CYAN, arrow_dir='down')

# Flow 6: ChromaDB -> MMR Retrieval (internal column connection)
draw_arrow_v(1200, 890, 1200, 938, label='Dense Similarity Search', color=ARROW_CYAN, direction='down')

# Flow 7: MMR Retrieval -> LLM Gateway
draw_arrow_orthogonal([
    (1530, 1135),
    (1580, 1135),
    (1580, 630),
    (1638, 630)
], label='Top-8 MMR Chunks', color=ARROW_CYAN, arrow_dir='right')

# Flow 8: LLM Gateway -> Academic Response Generation
draw_arrow_v(1970, 750, 1970, 798, label='Model Inference', color=ARROW_PURPLE, direction='down')

# Flow 9: Academic Response Generation -> Citation Engine
draw_arrow_v(1970, 1040, 1970, 1088, label='Raw Text & Citations', color=ARROW_GREEN, direction='down')

# Flow 10: Citation Engine -> Streamlit UI & Export Engine (Feedback loop up)
draw_arrow_orthogonal([
    (2300, 1210),
    (2350, 1210),
    (2350, 420),
    (2040, 420),
    (2040, 392)
], label='Verified Response + Citations [1][2]', color=ARROW_GREEN, arrow_dir='up')

# Flow 11: 4 Research Features -> Response Generation
draw_arrow_orthogonal([
    (1480, 390),
    (1480, 420),
    (1600, 420),
    (1600, 870),
    (1638, 870)
], label='Summary / Compare / Gap Commands', color=ARROW_PURPLE, arrow_dir='right')

# ==============================================================================
# 6. FOOTER LEGEND / METRICS BAR
# ==============================================================================
leg_y = 1395
draw.line([(70, leg_y - 15), (2330, leg_y - 15)], fill='#1b2d4b', width=1)

draw.text((80, leg_y), 'SYSTEM PIPELINE SPECIFICATION:', font=f_body_bold, fill=TEXT_MUTED)

def draw_legend_item(x, y, color, label):
    draw.rounded_rectangle([x, y + 2, x + 14, y + 16], radius=3, fill=color)
    draw.text((x + 22, y), label, font=f_body, fill=TEXT_LIGHT)
    bbox = f_body.getbbox(label)
    return x + 22 + (bbox[2] - bbox[0]) + 30

curr_x = 340
curr_x = draw_legend_item(curr_x, leg_y, TEAL_MAIN, 'Ingestion & Embeddings (pypdf + all-MiniLM-L6-v2)')
curr_x = draw_legend_item(curr_x, leg_y, CYAN_MAIN, 'Vector Storage & MMR Retrieval (ChromaDB Session)')
curr_x = draw_legend_item(curr_x, leg_y, PURPLE_ACCENT, 'Reasoning & LLM Gateway (Gemini 2.5 Flash + Groq Failover)')
curr_x = draw_legend_item(curr_x, leg_y, EMERALD_ACCENT, 'Citation Engine & Export (ReportLab PDF + DOCX)')

draw.text((2050, leg_y), 'Sant Baba Bhag Singh University', font=f_badge, fill=TEXT_MUTED)

# Save high-resolution PNG
img.save(out_path, 'PNG', quality=95, optimize=True)
print(f'Successfully generated {out_path} ({os.path.getsize(out_path)} bytes, {W}x{H})')

