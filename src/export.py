import io
import os
import sys
import re
from datetime import datetime

# Auto-detect local virtualenv site-packages if running under base Python
_workspace_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_venv_site = os.path.join(_workspace_root, ".myenv", "Lib", "site-packages")
if os.path.isdir(_venv_site) and _venv_site not in sys.path:
    sys.path.insert(0, _venv_site)

import docx
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH

from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    HRFlowable
)


import xml.sax.saxutils as saxutils


def _clean_markdown_inline(text: str) -> str:
    """Safely convert markdown styling to valid ReportLab XML."""
    if not text:
        return ""
    # 1. Escape XML characters first so <, >, & in academic text don't crash ReportLab
    safe_text = saxutils.escape(text)

    # 2. Convert markdown bold **...**
    safe_text = re.sub(r"\*\*(.*?)\*\*", r"<b>\1</b>", safe_text)

    # 3. Convert markdown italic *...* (avoiding double asterisks)
    safe_text = re.sub(r"(?<!\*)\*(?!\*)(.*?)(?<!\*)\*(?!\*)", r"<i>\1</i>", safe_text)

    # 4. Convert code `...`
    safe_text = re.sub(r"`(.*?)`", r"<font name='Courier'>\1</font>", safe_text)

    # 5. Handle any stray <br> into <br/>
    safe_text = re.sub(r"<br\s*>", r"<br/>", safe_text, flags=re.IGNORECASE)

    return safe_text


def _safe_paragraph(text: str, style) -> Paragraph:
    """Create a ReportLab Paragraph with fallback to pure plain text if XML parsing fails."""
    try:
        return Paragraph(text, style)
    except Exception:
        # Strip any bad tags and fall back to purely escaped text
        stripped = re.sub(r"<[^>]+>", "", text)
        escaped = saxutils.escape(stripped)
        return Paragraph(escaped, style)


def _parse_markdown_table(lines: list[str]) -> list[list[str]]:
    """Parse markdown table lines into 2D list of cells."""
    rows = []
    for line in lines:
        line = line.strip()
        if not line or not line.startswith("|"):
            continue
        # Skip separator line like |---|---|
        if re.match(r"^\|(\s*[-:]+[-|\s:]*)\|$", line):
            continue
        cells = [c.strip() for c in line.split("|")[1:-1]]
        if cells:
            rows.append(cells)
    return rows



def export_to_pdf(
    title: str,
    content: str,
    topic: str = "",
    citations: list = None,
    provider_info: str = ""
) -> bytes:
    """Generate a publication-ready academic research PDF report in-memory."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=48,
        leftMargin=48,
        topMargin=48,
        bottomMargin=48
    )

    styles = getSampleStyleSheet()

    # Custom styles
    title_style = ParagraphStyle(
        "ReportTitle",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=20,
        leading=24,
        textColor=colors.HexColor("#1e293b"),
        spaceAfter=6
    )

    subtitle_style = ParagraphStyle(
        "ReportSubtitle",
        parent=styles["Normal"],
        fontName="Helvetica-Oblique",
        fontSize=11,
        leading=14,
        textColor=colors.HexColor("#475569"),
        spaceAfter=4
    )

    meta_style = ParagraphStyle(
        "ReportMeta",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9,
        leading=12,
        textColor=colors.HexColor("#64748b"),
        spaceAfter=12
    )

    h1_style = ParagraphStyle(
        "SectionH1",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=14,
        leading=18,
        textColor=colors.HexColor("#0f172a"),
        spaceBefore=14,
        spaceAfter=6
    )

    h2_style = ParagraphStyle(
        "SectionH2",
        parent=styles["Heading3"],
        fontName="Helvetica-Bold",
        fontSize=12,
        leading=15,
        textColor=colors.HexColor("#1e3a8a"),
        spaceBefore=10,
        spaceAfter=4
    )

    body_style = ParagraphStyle(
        "BodyDark",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=10,
        leading=14,
        textColor=colors.HexColor("#334155"),
        spaceAfter=6
    )

    bullet_style = ParagraphStyle(
        "BulletText",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=10,
        leading=14,
        textColor=colors.HexColor("#334155"),
        leftIndent=15,
        spaceAfter=4
    )

    table_cell_style = ParagraphStyle(
        "TableCell",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8.5,
        leading=11,
        textColor=colors.HexColor("#1e293b")
    )

    table_header_style = ParagraphStyle(
        "TableHeader",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=9,
        leading=12,
        textColor=colors.white
    )

    elements = []

    # Title & Metadata
    elements.append(_safe_paragraph(title, title_style))
    if topic:
        elements.append(_safe_paragraph(f"<b>Research Topic / Focus:</b> {saxutils.escape(topic)}", subtitle_style))

    timestamp = datetime.now().strftime("%B %d, %Y at %H:%M")
    meta_text = f"<b>Generated by:</b> MSRA – Modular Smart Research Assistant &nbsp;|&nbsp; <b>Date:</b> {timestamp}"
    if provider_info:
        meta_text += f" &nbsp;|&nbsp; <b>Model Attribution:</b> {saxutils.escape(provider_info)}"
    elements.append(_safe_paragraph(meta_text, meta_style))
    elements.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#cbd5e1"), spaceAfter=14))

    if not content or not content.strip():
        elements.append(_safe_paragraph("<i>No content available for this section.</i>", body_style))
    else:
        raw_lines = content.split("\n")
        i = 0
        while i < len(raw_lines):
            line = raw_lines[i].strip()

            if not line:
                i += 1
                continue

            # Check for Markdown table block
            if line.startswith("|") and line.endswith("|"):
                table_lines = []
                while i < len(raw_lines) and raw_lines[i].strip().startswith("|"):
                    table_lines.append(raw_lines[i])
                    i += 1

                table_rows = _parse_markdown_table(table_lines)
                if table_rows:
                    formatted_table_data = []
                    for row_idx, row in enumerate(table_rows):
                        c_style = table_header_style if row_idx == 0 else table_cell_style
                        formatted_row = [
                            _safe_paragraph(_clean_markdown_inline(c), c_style) for c in row
                        ]
                        formatted_table_data.append(formatted_row)

                    t = Table(formatted_table_data, hAlign="LEFT")
                    t.setStyle(TableStyle([
                        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#1e3a8a")),
                        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
                        ('TOPPADDING', (0, 0), (-1, -1), 5),
                        ('LEFTPADDING', (0, 0), (-1, -1), 5),
                        ('RIGHTPADDING', (0, 0), (-1, -1), 5),
                        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.HexColor("#f8fafc"), colors.white])
                    ]))
                    elements.append(Spacer(1, 6))
                    elements.append(t)
                    elements.append(Spacer(1, 10))
                continue

            # Headings
            if line.startswith("### "):
                clean_h = _clean_markdown_inline(line[4:])
                elements.append(_safe_paragraph(clean_h, h2_style))
            elif line.startswith("## "):
                clean_h = _clean_markdown_inline(line[3:])
                elements.append(_safe_paragraph(clean_h, h1_style))
            elif line.startswith("# "):
                clean_h = _clean_markdown_inline(line[2:])
                elements.append(_safe_paragraph(clean_h, h1_style))
            elif line.startswith("- ") or line.startswith("* "):
                bullet_text = _clean_markdown_inline(line[2:])
                elements.append(_safe_paragraph(f"• &nbsp; {bullet_text}", bullet_style))
            elif re.match(r"^\d+\.\s", line):
                num_text = _clean_markdown_inline(line)
                elements.append(_safe_paragraph(num_text, bullet_style))
            else:
                body_p = _clean_markdown_inline(line)
                elements.append(_safe_paragraph(body_p, body_style))

            i += 1

    # Citations & References Section
    if citations:
        elements.append(Spacer(1, 12))
        elements.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#cbd5e1"), spaceAfter=10))
        elements.append(_safe_paragraph("📚 References & Source Citations", h1_style))

        ref_data = [[
            _safe_paragraph("<b>Citation Label</b>", table_header_style),
            _safe_paragraph("<b>Source Document</b>", table_header_style),
            _safe_paragraph("<b>Page Reference</b>", table_header_style)
        ]]

        seen_refs = set()
        for c in citations:
            label = str(c.get("citation_label", "[1]"))
            source = str(c.get("source", "Document"))
            page = str(c.get("page", "Page N/A"))
            ref_key = (label, source, page)
            if ref_key not in seen_refs:
                seen_refs.add(ref_key)
                ref_data.append([
                    _safe_paragraph(saxutils.escape(label), table_cell_style),
                    _safe_paragraph(saxutils.escape(source), table_cell_style),
                    _safe_paragraph(saxutils.escape(page), table_cell_style)
                ])

        ref_table = Table(ref_data, colWidths=[110, 280, 120], hAlign="LEFT")
        ref_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#334155")),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('LEFTPADDING', (0, 0), (-1, -1), 5),
            ('RIGHTPADDING', (0, 0), (-1, -1), 5),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.HexColor("#f8fafc"), colors.white])
        ]))
        elements.append(ref_table)

    doc.build(elements)
    buffer.seek(0)
    return buffer.getvalue()


def export_to_docx(
    title: str,
    content: str,
    topic: str = "",
    citations: list = None,
    provider_info: str = ""
) -> bytes:
    """Generate a clean academic research DOCX report in-memory."""
    document = docx.Document()

    # Document margins
    sections = document.sections
    for section in sections:
        section.top_margin = Inches(0.8)
        section.bottom_margin = Inches(0.8)
        section.left_margin = Inches(0.8)
        section.right_margin = Inches(0.8)

    # Document Title
    h1 = document.add_heading(title, level=0)
    h1.alignment = WD_ALIGN_PARAGRAPH.LEFT
    for run in h1.runs:
        run.font.name = "Calibri"
        run.font.color.rgb = RGBColor(30, 41, 59)

    # Subtitle / Topic
    if topic:
        sub_p = document.add_paragraph()
        run_sub = sub_p.add_run(f"Research Topic / Focus: {topic}")
        run_sub.font.italic = True
        run_sub.font.size = Pt(11)
        run_sub.font.color.rgb = RGBColor(71, 85, 105)

    # Metadata
    meta_p = document.add_paragraph()
    timestamp = datetime.now().strftime("%B %d, %Y at %H:%M")
    run_meta = meta_p.add_run(f"Generated by: MSRA – Modular Smart Research Assistant | Date: {timestamp}")
    if provider_info:
        run_meta.text += f" | Model Attribution: {provider_info}"
    run_meta.font.size = Pt(9.5)
    run_meta.font.color.rgb = RGBColor(100, 116, 139)

    document.add_paragraph("—" * 55)

    if not content or not content.strip():
        document.add_paragraph("No content available for this section.")
    else:
        raw_lines = content.split("\n")
        i = 0
        while i < len(raw_lines):
            line = raw_lines[i].strip()
            if not line:
                i += 1
                continue

            # Markdown Table Parsing
            if line.startswith("|") and line.endswith("|"):
                table_lines = []
                while i < len(raw_lines) and raw_lines[i].strip().startswith("|"):
                    table_lines.append(raw_lines[i])
                    i += 1

                table_rows = _parse_markdown_table(table_lines)
                if table_rows:
                    cols_count = len(table_rows[0])
                    doc_table = document.add_table(rows=len(table_rows), cols=cols_count)
                    doc_table.style = 'Light Shading Accent 1'

                    for r_idx, row in enumerate(table_rows):
                        for c_idx, cell_value in enumerate(row):
                            if c_idx < cols_count:
                                cell = doc_table.cell(r_idx, c_idx)
                                cell.text = re.sub(r"[*`]", "", cell_value)
                                if r_idx == 0:
                                    for p in cell.paragraphs:
                                        for r in p.runs:
                                            r.bold = True
                    document.add_paragraph()
                continue

            # Headings
            if line.startswith("### "):
                clean_h = re.sub(r"[*`]", "", line[4:])
                h = document.add_heading(clean_h, level=2)
                for r in h.runs:
                    r.font.color.rgb = RGBColor(30, 58, 138)
            elif line.startswith("## "):
                clean_h = re.sub(r"[*`]", "", line[3:])
                h = document.add_heading(clean_h, level=1)
                for r in h.runs:
                    r.font.color.rgb = RGBColor(15, 23, 42)
            elif line.startswith("# "):
                clean_h = re.sub(r"[*`]", "", line[2:])
                h = document.add_heading(clean_h, level=1)
            elif line.startswith("- ") or line.startswith("* "):
                clean_b = re.sub(r"[*`]", "", line[2:])
                document.add_paragraph(clean_b, style='List Bullet')
            elif re.match(r"^\d+\.\s", line):
                clean_n = re.sub(r"[*`]", "", line)
                document.add_paragraph(clean_n, style='List Number')
            else:
                p = document.add_paragraph()
                # Simple parser for bold chunks in body
                parts = re.split(r"(\*\*.*?\*\*)", line)
                for part in parts:
                    if part.startswith("**") and part.endswith("**"):
                        run = p.add_run(part[2:-2])
                        run.bold = True
                    else:
                        clean_text = re.sub(r"[`]", "", part)
                        p.add_run(clean_text)

            i += 1

    # References Table
    if citations:
        document.add_paragraph()
        document.add_paragraph("—" * 55)
        ref_h = document.add_heading("References & Source Citations", level=1)
        for r in ref_h.runs:
            r.font.color.rgb = RGBColor(15, 23, 42)

        unique_cites = []
        seen_refs = set()
        for c in citations:
            key = (str(c.get("citation_label", "")), str(c.get("source", "")), str(c.get("page", "")))
            if key not in seen_refs:
                seen_refs.add(key)
                unique_cites.append(c)

        ref_table = document.add_table(rows=len(unique_cites) + 1, cols=3)
        ref_table.style = 'Table Grid'

        headers = ["Citation Label", "Source Document", "Page Reference"]
        for idx, h_text in enumerate(headers):
            cell = ref_table.cell(0, idx)
            cell.text = h_text
            for p in cell.paragraphs:
                for run in p.runs:
                    run.bold = True

        for r_idx, c in enumerate(unique_cites, start=1):
            ref_table.cell(r_idx, 0).text = str(c.get("citation_label", f"[{r_idx}]"))
            ref_table.cell(r_idx, 1).text = str(c.get("source", "Document"))
            ref_table.cell(r_idx, 2).text = str(c.get("page", "Page N/A"))

    buffer = io.BytesIO()
    document.save(buffer)
    buffer.seek(0)
    return buffer.getvalue()
