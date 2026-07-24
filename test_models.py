import os
import requests

api_key = os.environ.get("GEMINI_API_KEY")
if not api_key:
    # try reading from .env
    with open(".env") as f:
        for line in f:
            if line.startswith("GEMINI_API_KEY="):
                api_key = line.strip().split("=")[1]
                break

if not api_key or api_key == "kendi_api_anahtarini_buraya_yapistir":
    print("No valid API key to test.")
else:
    url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
    resp = requests.get(url)
    if resp.status_code == 200:
        models = [m['name'] for m in resp.json().get('models', []) if 'flash' in m['name'].lower()]
        print("Available flash models:", models)
    else:
        print("Error fetching models:", resp.text)
