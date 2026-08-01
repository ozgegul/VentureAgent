"""PDF export helpers for VentureAgent module results.

Uses reportlab directly (not an HTML-to-PDF layer) because xhtml2pdf's CSS/HTML
pipeline drops Turkish letters (ş, ğ, ı, İ) even with a Unicode-capable font
embedded — reportlab's own text layer renders them correctly.
"""

from __future__ import annotations

import io
import os
from typing import Any

import font_roboto
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

_FONT_DIR = os.path.join(os.path.dirname(font_roboto.__file__), "files")
_fonts_registered = False


def _ensure_fonts_registered() -> None:
    """Register the bundled Roboto font (covers Turkish characters) once per process."""
    global _fonts_registered
    if _fonts_registered:
        return
    pdfmetrics.registerFont(TTFont("Roboto", os.path.join(_FONT_DIR, "Roboto-Regular.ttf")))
    pdfmetrics.registerFont(TTFont("Roboto-Bold", os.path.join(_FONT_DIR, "Roboto-Bold.ttf")))
    _fonts_registered = True


_QUADRANTS = [
    ("strengths", "Güçlü Yönler", "#007c72"),
    ("weaknesses", "Zayıf Yönler", "#ef6a4d"),
    ("opportunities", "Fırsatlar", "#f5b942"),
    ("threats", "Tehditler", "#6b5cff"),
]


def build_swot_pdf(*, idea: str, sector: str | None, swot: dict[str, Any]) -> bytes:
    """Render a SWOT analysis result as a 2x2 quadrant PDF and return its bytes."""
    _ensure_fonts_registered()

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        topMargin=18 * mm,
        bottomMargin=16 * mm,
        leftMargin=16 * mm,
        rightMargin=16 * mm,
        title=f"SWOT Analizi — {idea}",
    )

    title_style = ParagraphStyle(
        "Title", fontName="Roboto-Bold", fontSize=18, leading=22, textColor=colors.HexColor("#17201c")
    )
    meta_style = ParagraphStyle(
        "Meta", fontName="Roboto", fontSize=10, leading=14, textColor=colors.HexColor("#66706b"), spaceAfter=14
    )
    quadrant_title_style = ParagraphStyle(
        "QuadrantTitle", fontName="Roboto-Bold", fontSize=11, leading=14, textColor=colors.white
    )
    item_style = ParagraphStyle("Item", fontName="Roboto", fontSize=9.5, leading=13, textColor=colors.white)
    empty_style = ParagraphStyle(
        "Empty", fontName="Roboto", fontSize=9.5, leading=13, textColor=colors.HexColor("#f0f0f0")
    )

    def quadrant_cell(key: str, label: str, hex_color: str) -> Table:
        items = swot.get(key) or []
        rows = [[Paragraph(label, quadrant_title_style)]]
        if items:
            for item in items:
                rows.append([Paragraph(f"&#8226;&nbsp; {item}", item_style)])
        else:
            rows.append([Paragraph("Belirtilmedi", empty_style)])

        cell = Table(rows, colWidths=[82 * mm])
        cell.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor(hex_color)),
                    ("LEFTPADDING", (0, 0), (-1, -1), 10),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                    ("TOPPADDING", (0, 0), (0, 0), 10),
                    ("BOTTOMPADDING", (0, 0), (0, 0), 6),
                    ("TOPPADDING", (0, 1), (-1, -1), 1),
                    ("BOTTOMPADDING", (0, 1), (-1, -2), 1),
                    ("BOTTOMPADDING", (0, -1), (-1, -1), 10),
                ]
            )
        )
        return cell

    elements: list[Any] = [
        Paragraph("VentureAgent — SWOT Analizi", title_style),
        Paragraph(
            f"{idea}" + (f" &middot; Sektör: {sector}" if sector else ""),
            meta_style,
        ),
    ]

    cells = [quadrant_cell(key, label, hex_color) for key, label, hex_color in _QUADRANTS]
    grid = Table(
        [[cells[0], cells[1]], [cells[2], cells[3]]],
        colWidths=[85 * mm, 85 * mm],
    )
    grid.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (0, -1), 4),
                ("LEFTPADDING", (1, 0), (1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 4),
                ("BOTTOMPADDING", (0, 1), (-1, 1), 0),
            ]
        )
    )
    elements.append(grid)
    elements.append(Spacer(1, 16))
    elements.append(Paragraph("VentureAgent ile oluşturuldu.", meta_style))

    doc.build(elements)
    return buffer.getvalue()
