"""
Programmatic bank statement PDF generator for Phase 7 real-world testing.
Generates realistic, syntactically and visually diverse PDF bank statements
using ReportLab canvas and tables.
"""
from datetime import date
import os
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors


def create_statement_pdf(
    file_path: str,
    bank_name: str,
    account_holder: str,
    account_no: str,
    headers: list[str],
    col_x_positions: list[float],
    rows_data: list[list[str]],
    date_format: str = "DD/MM/YYYY",
    header_noise: list[str] | None = None,
    footer_noise: list[str] | None = None,
    page_break_after_rows: list[int] | None = None,
    repeat_headers: bool = False,
    table_bordered: bool = False,
    irregular_spacing: bool = False,
):
    """
    Creates a bank statement PDF matching specific structural parameters.
    Can generate borderless text layouts using canvas or bordered tables.
    """
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    c = canvas.Canvas(file_path, pagesize=A4)
    width, height = A4

    current_page = 1
    y = height - 50

    # Draw header noise / bank branding
    c.setFont("Helvetica-Bold", 14)
    c.drawString(50, y, bank_name)
    y -= 18

    c.setFont("Helvetica", 9)
    if header_noise:
        for hn in header_noise:
            c.drawString(50, y, hn)
            y -= 13

    c.drawString(50, y, f"Account Holder: {account_holder}")
    c.drawString(320, y, f"Account Number: {account_no}")
    y -= 14
    c.drawString(50, y, "Account Type: Savings")
    c.drawString(320, y, "Statement Period: 01/08/2026 to 31/08/2026")
    y -= 25

    def draw_headers():
        nonlocal y
        c.setFont("Helvetica-Bold", 8.5)
        if table_bordered:
            c.setStrokeColor(colors.black)
            c.line(45, y + 10, width - 45, y + 10)
        for h, x in zip(headers, col_x_positions):
            c.drawString(x, y, h)
        y -= 14
        if table_bordered:
            c.line(45, y + 10, width - 45, y + 10)

    draw_headers()

    c.setFont("Helvetica", 8)
    row_count = 0
    page_break_set = set(page_break_after_rows or [])

    for row_cells in rows_data:
        row_count += 1

        # Check if line contains multi-line narration (newline in description)
        line_height = 14
        extra_lines = []
        for i, text in enumerate(row_cells):
            x = col_x_positions[i]
            if "\n" in text:
                parts = text.split("\n")
                c.drawString(x, y, parts[0])
                for extra_idx, part in enumerate(parts[1:], start=1):
                    extra_lines.append((x, part, extra_idx))
            else:
                x_offset = 3 if irregular_spacing and i % 2 == 1 else 0
                c.drawString(x + x_offset, y, text)

        if extra_lines:
            max_extra = max(el[2] for el in extra_lines)
            for el_x, el_text, el_idx in extra_lines:
                c.drawString(el_x, y - (el_idx * 11), el_text)
            y -= (max_extra * 11)

        y -= line_height

        if row_count in page_break_set:
            # Draw footer noise before pagebreak
            if footer_noise:
                c.setFont("Helvetica-Oblique", 7.5)
                c.drawString(50, 40, footer_noise[0])
                c.drawString(450, 40, f"Page {current_page} of 2")

            c.showPage()
            current_page += 1
            y = height - 50

            if repeat_headers:
                c.setFont("Helvetica-Bold", 11)
                c.drawString(50, y, f"{bank_name} (Continued)")
                y -= 20
                draw_headers()
            c.setFont("Helvetica", 8)

    # Final footer noise
    if footer_noise:
        c.setFont("Helvetica-Oblique", 7.5)
        c.drawString(50, 40, footer_noise[0])
        c.drawString(450, 40, f"Page {current_page} of {current_page}")

    c.save()
    return file_path
