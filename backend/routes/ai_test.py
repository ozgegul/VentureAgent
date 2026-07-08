"""AI provider test route."""

from flask import Blueprint, render_template, request

from backend.services.ai_client import ask_ai, get_ai_provider

ai_test_bp = Blueprint("ai_test", __name__, template_folder="../../frontend/templates")


@ai_test_bp.route("/", methods=["GET", "POST"])
def ai_test_page():
    """Render an AI provider test page."""
    result = None
    error = None
    prompt = "VentureAgent projesini Türkçe ve tek paragrafta açıkla."

    if request.method == "POST":
        prompt = request.form.get("prompt", "").strip()
        if not prompt:
            error = "Prompt boş olamaz."
        else:
            try:
                result = ask_ai(prompt, max_tokens=300)
            except Exception as exc:  # noqa: BLE001
                error = str(exc)

    return render_template(
        "ai_test.html",
        provider=get_ai_provider(),
        prompt=prompt,
        result=result,
        error=error,
    )
