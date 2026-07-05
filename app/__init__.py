"""
Flask application factory.
run.py bu fonksiyonu çağırarak uygulamayı başlatır.
"""

import os
from flask import Flask
from dotenv import load_dotenv

load_dotenv()  # .env dosyasındaki değişkenleri yükler


def create_app():
    app = Flask(__name__)
    app.config["SECRET_KEY"] = os.environ.get("FLASK_SECRET_KEY", "dev-secret-key")

    # Blueprint'leri kaydet
    from app.routes.main import main_bp
    from app.routes.chat import chat_bp
    from app.routes.idea import idea_bp
    from app.routes.swot import swot_bp
    from app.routes.competitors import competitors_bp
    from app.routes.revenue import revenue_bp
    from app.routes.roadmap import roadmap_bp
    from app.routes.kanban import kanban_bp
    from app.routes.investors import investors_bp
    from app.routes.pitch import pitch_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(chat_bp, url_prefix="/chat")
    app.register_blueprint(idea_bp, url_prefix="/idea")
    app.register_blueprint(swot_bp, url_prefix="/swot")
    app.register_blueprint(competitors_bp, url_prefix="/competitors")
    app.register_blueprint(revenue_bp, url_prefix="/revenue")
    app.register_blueprint(roadmap_bp, url_prefix="/roadmap")
    app.register_blueprint(kanban_bp, url_prefix="/kanban")
    app.register_blueprint(investors_bp, url_prefix="/investors")
    app.register_blueprint(pitch_bp, url_prefix="/pitch")

    return app
