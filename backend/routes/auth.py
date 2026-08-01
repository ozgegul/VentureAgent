"""Kayıt, giriş, çıkış ve e-posta doğrulama rotaları."""

from __future__ import annotations

import random
import re
from datetime import datetime, timedelta

from flask import Blueprint, flash, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from backend.auth import current_user, login_required
from backend.database import (
    create_user,
    get_user_by_email,
    mark_email_verified,
    set_verification_code,
    update_user_role,
)
from backend.services.mailer import EmailSendError, send_verification_email

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


VERIFICATION_CODE_TTL_MINUTES = 15


def _issue_verification_code(user: dict) -> None:
    """Generate a fresh 6-digit code, store it, and email it to the user.

    E-posta gönderimi başarısız olursa (SMTP hatası) kod yine de DB'ye
    kaydedilir — kullanıcı 'kodu yeniden gönder' ile tekrar deneyebilir;
    akış tamamen tıkanmaz.
    """
    code = f"{random.randint(0, 999999):06d}"
    expires_at = (datetime.utcnow() + timedelta(minutes=VERIFICATION_CODE_TTL_MINUTES)).isoformat()
    set_verification_code(user["id"], code, expires_at)
    try:
        send_verification_email(to=user["email"], name=user["name"], code=code)
    except EmailSendError:
        # Kod DB'de duruyor; kullanıcı "yeniden gönder"i deneyebilir.
        # Yerel geliştirmede mailer zaten kodu konsola basar (bkz. mailer.py).
        pass


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
    user = get_user_by_email(email)
    _issue_verification_code(user)
    flash("Hesabın oluşturuldu. E-postana gönderdiğimiz kodu girerek doğrula.", "success")
    return redirect(url_for("auth.verify", email=email))


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

    if not user["email_verified"]:
        _issue_verification_code(user)
        flash("Hesabını henüz doğrulamadın. E-postana yeni bir kod gönderdik.", "error")
        return redirect(url_for("auth.verify", email=email))

    session.clear()
    session["user_id"] = user["id"]
    flash(f"Tekrar hoş geldin, {user['name']}!", "success")
    return redirect(next_url)


@auth_bp.route("/logout", methods=["POST"])
def logout():
    session.clear()
    flash("Çıkış yapıldı.", "success")
    return redirect(url_for("main.index"))


@auth_bp.route("/verify", methods=["GET", "POST"])
def verify():
    """E-posta doğrulama kodu giriş sayfası."""
    if current_user():
        return redirect(url_for("main.index"))

    email = request.values.get("email", "").strip().lower()
    user = get_user_by_email(email) if email else None

    if user is None:
        flash("Doğrulanacak bir hesap bulunamadı.", "error")
        return redirect(url_for("auth.register"))

    if user["email_verified"]:
        flash("Bu hesap zaten doğrulanmış. Giriş yapabilirsin.", "success")
        return redirect(url_for("auth.login"))

    if request.method == "GET":
        return render_template("auth/verify.html", email=email)

    code = request.form.get("code", "").strip()
    error = None

    if not user["verification_code"] or not user["verification_expires_at"]:
        error = "Kod bulunamadı. Lütfen yeni bir kod iste."
    elif datetime.utcnow() > datetime.fromisoformat(user["verification_expires_at"]):
        error = "Kodun süresi dolmuş. Lütfen yeni bir kod iste."
    elif code != user["verification_code"]:
        error = "Girdiğin kod hatalı."

    if error:
        return render_template("auth/verify.html", email=email, error=error)

    mark_email_verified(user["id"])
    session.clear()
    session["user_id"] = user["id"]
    flash("E-postan doğrulandı! Hoş geldin. 🎉", "success")
    return redirect(url_for("main.index"))


@auth_bp.route("/verify/resend", methods=["POST"])
def resend_verification():
    """Doğrulama kodunu yeniden gönderir."""
    email = request.form.get("email", "").strip().lower()
    user = get_user_by_email(email) if email else None

    if user is None:
        flash("Hesap bulunamadı.", "error")
        return redirect(url_for("auth.register"))

    if user["email_verified"]:
        return redirect(url_for("auth.login"))

    _issue_verification_code(user)
    flash("Yeni kod e-postana gönderildi.", "success")
    return redirect(url_for("auth.verify", email=email))


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
