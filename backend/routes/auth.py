"""Kayıt, giriş ve çıkış rotaları."""

from __future__ import annotations

import re

from flask import Blueprint, flash, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from backend.auth import current_user
from backend.database import create_user, get_user_by_email

auth_bp = Blueprint("auth", __name__, template_folder="../../frontend/templates")

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


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
        error = "Geçerli bir e-posta adresi girin."
    elif len(password) < 8:
        error = "Şifre en az 8 karakter olmalıdır."
    elif password != password_confirm:
        error = "Şifreler eşleşmiyor."
    elif get_user_by_email(email) is not None:
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
