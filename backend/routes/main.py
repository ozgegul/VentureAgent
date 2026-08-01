from flask import Blueprint, render_template

from backend.auth import current_user
from backend.database import (
    get_homepage_stats,
    get_module_usage_breakdown,
    get_risk_level_distribution,
    get_user_activity_series,
    get_user_growth_series,
)

main_bp = Blueprint("main", __name__)


@main_bp.route("/")
def index():
    user = current_user()

    if user:
        return render_template(
            "index.html",
            is_personal=True,
            stats=get_homepage_stats(user_id=user["id"]),
            activity_series=get_user_activity_series(user["id"]),
            module_usage=get_module_usage_breakdown(user_id=user["id"]),
            risk_distribution=get_risk_level_distribution(user_id=user["id"]),
        )

    return render_template(
        "index.html",
        is_personal=False,
        stats=get_homepage_stats(),
        activity_series=get_user_growth_series(),
        module_usage=get_module_usage_breakdown(),
        risk_distribution=get_risk_level_distribution(),
    )
