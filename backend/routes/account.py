"""Hesap paneli: profil bilgisi, şifre değiştirme, profil fotoğrafı, kendi geçmişi."""

from __future__ import annotations

import io
import uuid
from pathlib import Path

from flask import Blueprint, current_app, flash, redirect, render_template, request, url_for
from PIL import Image, UnidentifiedImageError
from werkzeug.security import check_password_hash, generate_password_hash

from backend.auth import current_user, login_required
from backend.database import (
    get_dashboard_metrics,
    list_idea_analyses,
    list_module_results,
    update_user_avatar,
    update_user_password,
)
from backend.routes.auth import validate_password
from backend.routes.history import MODULE_LABELS

account_bp = Blueprint("account", __name__, template_folder="../../frontend/templates")

ALLOWED_AVATAR_TYPES = {"image/jpeg", "image/png", "image/webp"}
MAX_AVATAR_BYTES = 3 * 1024 * 1024  # 3MB — global 10MB istek limitinden daha sıkı
AVATAR_OUTPUT_SIZE = (320, 320)


def _avatar_dir() -> Path:
    path = Path(current_app.static_folder) / "uploads" / "avatars"
    path.mkdir(parents=True, exist_ok=True)
    return path


@account_bp.route("/", methods=["GET"])
@login_required
def account_page():
    user = current_user()
    metrics = get_dashboard_metrics(user["id"])
    recent_analyses = list_idea_analyses(user["id"], limit=5)
    recent_modules = list_module_results(user["id"], limit=5)
    for result in recent_modules:
        result["label"] = MODULE_LABELS.get(result["module"], result["module"])
    return render_template(
        "account/dashboard.html",
        metrics=metrics,
        recent_analyses=recent_analyses,
        recent_modules=recent_modules,
    )


@account_bp.route("/password", methods=["POST"])
@login_required
def change_password():
    user = current_user()
    current_password = request.form.get("current_password", "")
    new_password = request.form.get("new_password", "")
    new_password_confirm = request.form.get("new_password_confirm", "")

    error = None
    if not check_password_hash(user["password_hash"], current_password):
        error = "Mevcut şifren yanlış."
    elif new_password != new_password_confirm:
        error = "Yeni şifreler eşleşmiyor."
    else:
        error = validate_password(new_password)

    if error:
        flash(error, "error")
        return redirect(url_for("account.account_page"))

    update_user_password(user["id"], generate_password_hash(new_password))
    flash("Şifren güncellendi.", "success")
    return redirect(url_for("account.account_page"))


@account_bp.route("/avatar", methods=["POST"])
@login_required
def upload_avatar():
    user = current_user()
    file = request.files.get("avatar")

    if file is None or file.filename == "":
        flash("Bir fotoğraf seçmelisin.", "error")
        return redirect(url_for("account.account_page"))

    raw = file.read()
    if len(raw) > MAX_AVATAR_BYTES:
        flash("Fotoğraf 3MB'tan küçük olmalıdır.", "error")
        return redirect(url_for("account.account_page"))

    # Dosya uzantısına/MIME başlığına güvenmek yerine, gerçekten geçerli bir
    # görsel olduğunu Pillow ile doğrula ve sabit boyuta getirerek yeniden
    # kaydet — bu hem kötü niyetli dosyaları eler hem de tutarlı bir görünüm
    # sağlar.
    try:
        image = Image.open(io.BytesIO(raw))
        image.verify()
        image = Image.open(io.BytesIO(raw))  # verify() sonrası yeniden aç
        image = image.convert("RGB")
    except (UnidentifiedImageError, OSError):
        flash("Geçersiz bir görsel dosyası. JPG, PNG veya WEBP yükle.", "error")
        return redirect(url_for("account.account_page"))

    image.thumbnail(AVATAR_OUTPUT_SIZE)
    filename = f"{uuid.uuid4().hex}.jpg"
    output_path = _avatar_dir() / filename
    image.save(output_path, "JPEG", quality=88)

    # Eski avatarı temizle (varsa)
    old_avatar = user.get("avatar_path")
    if old_avatar:
        old_path = Path(current_app.static_folder) / old_avatar
        if old_path.exists() and old_path.is_relative_to(_avatar_dir()):
            old_path.unlink(missing_ok=True)

    update_user_avatar(user["id"], f"uploads/avatars/{filename}")
    flash("Profil fotoğrafın güncellendi.", "success")
    return redirect(url_for("account.account_page"))


@account_bp.route("/avatar/delete", methods=["POST"])
@login_required
def delete_avatar():
    user = current_user()
    old_avatar = user.get("avatar_path")
    if old_avatar:
        old_path = Path(current_app.static_folder) / old_avatar
        if old_path.exists() and old_path.is_relative_to(_avatar_dir()):
            old_path.unlink(missing_ok=True)
    update_user_avatar(user["id"], None)
    flash("Profil fotoğrafın kaldırıldı.", "success")
    return redirect(url_for("account.account_page"))
