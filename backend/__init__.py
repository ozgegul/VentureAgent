"""
Flask application factory.
run.py bu fonksiyonu çağırarak uygulamayı başlatır.
"""

import os
from flask import Flask
from dotenv import load_dotenv

load_dotenv()  # .env dosyasındaki değişkenleri yükler


def create_app():
    app = Flask(
        __name__,
        template_folder="../frontend/templates",
        static_folder="../frontend/static",
    )
    app.config["SECRET_KEY"] = os.environ.get("FLASK_SECRET_KEY", "dev-secret-key")

    from backend.database import init_app

    init_app(app)

    # Blueprint'leri kaydet
    from backend.routes.main import main_bp
    from backend.routes.ai_test import ai_test_bp
    from backend.routes.chat import chat_bp
    from backend.routes.dashboard import dashboard_bp
    from backend.routes.guided import guided_bp
    from backend.routes.history import history_bp
    from backend.routes.idea import idea_bp
    from backend.routes.swot import swot_bp
    from backend.routes.competitors import competitors_bp
    from backend.routes.revenue import revenue_bp
    from backend.routes.roadmap import roadmap_bp
    from backend.routes.kanban import kanban_bp
    from backend.routes.investors import investors_bp
    from backend.routes.pitch import pitch_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(ai_test_bp, url_prefix="/ai-test")
    app.register_blueprint(chat_bp, url_prefix="/chat")
    app.register_blueprint(dashboard_bp, url_prefix="/dashboard")
    app.register_blueprint(guided_bp, url_prefix="/guided")
    app.register_blueprint(history_bp, url_prefix="/history")
    app.register_blueprint(idea_bp, url_prefix="/idea")
    app.register_blueprint(swot_bp, url_prefix="/swot")
    app.register_blueprint(competitors_bp, url_prefix="/competitors")
    app.register_blueprint(revenue_bp, url_prefix="/revenue")
    app.register_blueprint(roadmap_bp, url_prefix="/roadmap")
    app.register_blueprint(kanban_bp, url_prefix="/kanban")
    app.register_blueprint(investors_bp, url_prefix="/investors")
    app.register_blueprint(pitch_bp, url_prefix="/pitch")

    return app
