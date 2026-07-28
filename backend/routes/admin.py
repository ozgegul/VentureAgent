"""Admin panel: kullanıcı listesi, rol/durum yönetimi, platform metrikleri.

Tüm route'lar `role_required("admin")` ile korunur.
"""

from __future__ import annotations

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for

from backend.auth import current_user, role_required
from backend.database import (
    ROLES,
    get_platform_metrics,
    get_user_by_id,
    list_users,
    set_user_active,
    update_user_role,
)

admin_bp = Blueprint("admin", __name__, template_folder="../../frontend/templates")


@admin_bp.route("/")
@role_required("admin")
def admin_dashboard():
    """Show platform-wide metrics and the user list."""
    metrics = get_platform_metrics()
    users = list_users()
    return render_template("admin/dashboard.html", metrics=metrics, users=users, roles=ROLES)


@admin_bp.route("/users/<int:user_id>/role", methods=["POST"])
@role_required("admin")
def change_role(user_id: int):
    """Update a user's role (free/pro/admin)."""
    target = get_user_by_id(user_id)
    if target is None:
        abort(404)

    new_role = request.form.get("role", "")
    if new_role not in ROLES:
        flash("Geçersiz rol.", "error")
        return redirect(url_for("admin.admin_dashboard"))

    if target["id"] == current_user()["id"] and new_role != "admin":
        # Kendi admin yetkisini kazayla düşürmesini engelle.
        flash("Kendi admin rolünüzü buradan kaldıramazsınız.", "error")
        return redirect(url_for("admin.admin_dashboard"))

    update_user_role(user_id, new_role)
    flash(f"{target['name']} kullanıcısının rolü '{new_role}' olarak güncellendi.", "success")
    return redirect(url_for("admin.admin_dashboard"))


@admin_bp.route("/users/<int:user_id>/toggle-active", methods=["POST"])
@role_required("admin")
def toggle_active(user_id: int):
    """Activate or deactivate (soft-ban) a user account."""
    target = get_user_by_id(user_id)
    if target is None:
        abort(404)

    if target["id"] == current_user()["id"]:
        flash("Kendi hesabınızı devre dışı bırakamazsınız.", "error")
        return redirect(url_for("admin.admin_dashboard"))

    set_user_active(user_id, not target["is_active"])
    state = "aktifleştirildi" if not target["is_active"] else "devre dışı bırakıldı"
    flash(f"{target['name']} hesabı {state}.", "success")
    return redirect(url_for("admin.admin_dashboard"))
