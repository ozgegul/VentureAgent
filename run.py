"""
Uygulamayı başlatan giriş noktası.

Kullanım:
    python run.py
"""

import os
from app import create_app

app = create_app()

if __name__ == "__main__":
    debug = os.environ.get("FLASK_DEBUG", "False") == "True"
    app.run(debug=debug, port=5000)
