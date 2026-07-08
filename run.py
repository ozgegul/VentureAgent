"""
Uygulamayı başlatan giriş noktası.

Kullanım:
    python run.py
"""

import os
from backend import create_app

app = create_app()

if __name__ == "__main__":
    debug = os.environ.get("FLASK_DEBUG", "False") == "True"
    port = int(os.environ.get("PORT", "5000"))
    app.run(debug=debug, port=port)