"""Kayıt, giriş ve çıkış rotaları."""

from __future__ import annotations

import re

from flask import Blueprint, flash, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from backend.auth import current_user, login_required
from backend.database import create_user, get_user_by_email, update_user_role

auth_bp = Blueprint("auth", __name__, template_folder="../../frontend/templates")

EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")

# Yaygın sağlayıcılarda sık yapılan yazım hataları (örn. gmail.co -> gmail.com).
# Tam doğrulama için e-postaya onay linki göndermek gerekir (bu henüz yok);
# bu liste en azından en sık görülen yazım hatalarını yakalar.
COMMON_DOMAIN_TYPOS = {
    "gmail.co": "gmail.com",
    "gmail.con": "gmail.com",
    "gmail.cm": "gmail.com",
    "gmai.com": "gmail.com",
    "gmial.com": "gmail.com",
    "hotmail.co": "hotmail.com",
    "hotmial.com": "hotmail.com",
    "outlook.co": "outlook.com",
    "yahoo.co": "yahoo.com",
    "yaho.com": "yahoo.com",
}


def validate_password(password: str) -> str | None:
    """Return an error message if the password is too weak, else None."""
    if len(password) < 8:
        return "Şifre en az 8 karakter olmalıdır."
    if len(set(password)) == 1:
        return "Şifre tek bir karakterin tekrarından oluşamaz (örn. 11111111)."
    if not re.search(r"[A-Za-z]", password):
        return "Şifre en az bir harf içermelidir."
    if not re.search(r"[0-9]", password):
        return "Şifre en az bir rakam içermelidir."
    return None


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user():
        return redirect(url_for("main.index"))

    if request.method == "GET":
        return render_template("auth/register.html")

    name = request.form.get("name", "").strip()
    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")
    password_confirm = request.form.get("password_confirm", "")

    error = None
    if not name or not email or not password:
        error = "Ad, e-posta ve şifre alanları zorunludur."
    elif not EMAIL_RE.match(email):
        error = "Geçerli bir e-posta adresi girin (örn. isim@site.com)."
    elif email.split("@")[-1] in COMMON_DOMAIN_TYPOS:
        suggestion = COMMON_DOMAIN_TYPOS[email.split("@")[-1]]
        error = f"'{email}' geçerli görünmüyor. '{suggestion}' mi demek istedin?"
    else:
        error = validate_password(password)

    if error is None and password != password_confirm:
        error = "Şifreler eşleşmiyor."
    if error is None and get_user_by_email(email) is not None:
        error = "Bu e-posta adresi zaten kayıtlı."

    if error:
        return render_template("auth/register.html", error=error, name=name, email=email)

    user_id = create_user(
        name=name,
        email=email,
        password_hash=generate_password_hash(password),
        role="free",
    )
    session.clear()
    session["user_id"] = user_id
    flash("Hesabınız oluşturuldu. Hoş geldiniz!", "success")
    return redirect(url_for("main.index"))


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user():
        return redirect(url_for("main.index"))

    if request.method == "GET":
        return render_template("auth/login.html", next=request.args.get("next", ""))

    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")
    next_url = request.form.get("next") or url_for("main.index")

    user = get_user_by_email(email)
    error = None
    if user is None or not check_password_hash(user["password_hash"], password):
        error = "E-posta veya şifre hatalı."
    elif not user["is_active"]:
        error = "Bu hesap devre dışı bırakılmış. Destek ile iletişime geçin."

    if error:
        return render_template("auth/login.html", error=error, email=email, next=next_url)

    session.clear()
    session["user_id"] = user["id"]
    flash(f"Tekrar hoş geldin, {user['name']}!", "success")
    return redirect(next_url)


@auth_bp.route("/logout", methods=["POST"])
def logout():
    session.clear()
    flash("Çıkış yapıldı.", "success")
    return redirect(url_for("main.index"))


@auth_bp.route("/upgrade", methods=["GET"])
@login_required
def upgrade_page():
    """Pro'ya geçiş için sahte (placeholder) ödeme sayfasını gösterir."""
    user = current_user()
    if user["role"] != "free":
        flash("Zaten Pro veya Admin hesabın var.", "success")
        return redirect(url_for("main.index"))
    return render_template("auth/upgrade.html")


@auth_bp.route("/upgrade", methods=["POST"])
@login_required
def process_upgrade():
    """Sahte ödeme formunu 'işler' ve kullanıcıyı Pro'ya geçirir.

    GEÇİCİ/DEMO: Gerçek bir ödeme sağlayıcısı (Stripe/iyzico vb.) bağlanana
    kadar kart bilgileri hiçbir yere gönderilmiyor, gerçek bir tahsilat
    yapılmıyor — sadece dolu mu diye bakılıyor. Gerçek entegrasyon
    eklendiğinde bu route sağlayıcının ödeme onayı/webhook'u ile
    değiştirilmelidir.
    """
    user = current_user()
    if user["role"] != "free":
        return redirect(url_for("main.index"))

    card_number = request.form.get("card_number", "").replace(" ", "")
    card_name = request.form.get("card_name", "").strip()
    expiry = request.form.get("expiry", "").strip()
    cvv = request.form.get("cvv", "").strip()

    error = None
    if not card_name:
        error = "Kart üzerindeki isim zorunludur."
    elif not card_number.isdigit() or len(card_number) != 16:
        error = "Kart numarası 16 haneli olmalıdır."
    elif not re.match(r"^\d{2}/\d{2}$", expiry):
        error = "Son kullanma tarihi AA/YY formatında olmalıdır."
    elif not cvv.isdigit() or len(cvv) not in (3, 4):
        error = "CVV 3 veya 4 haneli olmalıdır."

    if error:
        return render_template("auth/upgrade.html", error=error, card_name=card_name)

    update_user_role(user["id"], "pro")
    flash("Ödeme alındı (demo) — Pro'ya hoş geldin! 🎉", "success")
    return redirect(url_for("main.index"))
