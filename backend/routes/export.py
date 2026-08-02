"""
PPTX Export Route'ları

Pitch deck ve Yatırımcı raporu için PowerPoint indirme endpoint'lerini
barındırır. Mevcut Flask blueprint mimarisine uygun olarak eklendi.
"""

import json

from flask import Blueprint, request, send_file, redirect, url_for, flash
import io

from backend.auth import login_required
from backend.services.pptx_export import build_pitch_pptx, build_investors_pptx

export_bp = Blueprint("export", __name__)


@export_bp.route("/pitch", methods=["POST"])
@login_required
def pitch_pptx():
    """Pitch deck slaytlarını PPTX olarak indirir."""
    idea = request.form.get("idea", "").strip()
    slides_json = request.form.get("slides_json", "[]")

    try:
        slides = json.loads(slides_json)
    except (json.JSONDecodeError, ValueError):
        flash("Slayt verisi okunamadı.", "error")
        return redirect(url_for("pitch.pitch_form"))

    if not slides:
        flash("İndirilecek slayt verisi bulunamadı.", "error")
        return redirect(url_for("pitch.pitch_form"))

    pptx_bytes = build_pitch_pptx(idea=idea, slides=slides)

    return send_file(
        io.BytesIO(pptx_bytes),
        mimetype="application/vnd.openxmlformats-officedocument.presentationml.presentation",
        as_attachment=True,
        download_name="pitch_deck.pptx",
    )


@export_bp.route("/investors", methods=["POST"])
@login_required
def investors_pptx():
    """Yatırımcı tavsiye raporunu PPTX olarak indirir."""
    idea = request.form.get("idea", "").strip()
    advice = request.form.get("advice", "").strip()

    if not advice:
        flash("İndirilecek tavsiye verisi bulunamadı.", "error")
        return redirect(url_for("investors.investors_form"))

    pptx_bytes = build_investors_pptx(idea=idea, advice=advice)

    return send_file(
        io.BytesIO(pptx_bytes),
        mimetype="application/vnd.openxmlformats-officedocument.presentationml.presentation",
        as_attachment=True,
        download_name="yatirimci_raporu.pptx",
    )
