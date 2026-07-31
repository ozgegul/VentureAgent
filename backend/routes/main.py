from flask import Blueprint, render_template

from backend.database import (
    get_homepage_stats,
    get_module_usage_breakdown,
    get_risk_level_distribution,
    get_user_growth_series,
)

main_bp = Blueprint("main", __name__)


@main_bp.route("/")
def index():
    return render_template(
        "index.html",
        stats=get_homepage_stats(),
        user_growth=get_user_growth_series(),
        module_usage=get_module_usage_breakdown(),
        risk_distribution=get_risk_level_distribution(),
    )
