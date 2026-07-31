# VentureAgent — Developer Onboarding Guide

Welcome to the **VentureAgent** project! This document is designed to help new software engineers quickly understand the project's purpose, technology stack, architecture, and how to get the local development environment running.

---

## 1. Project Purpose & Executive Summary

**VentureAgent** is an AI-powered web application that serves as a virtual co-founder and startup consultant. It helps entrepreneurs and aspiring founders take an idea and turn it into a structured, actionable business plan. 

Instead of going through expensive and time-consuming consultancy processes, a user can input their startup idea in plain text. VentureAgent then analyzes the idea, validates it, and generates various business outputs such as:
- **Idea Analysis & Venture Score:** Evaluates strengths, weaknesses, and readiness.
- **SWOT Analysis:** Identifies Strengths, Weaknesses, Opportunities, and Threats.
- **Competitor Research:** Finds potential competitors and positioning strategies.
- **Revenue Models:** Suggests how to monetize the idea.
- **MVP Roadmap & Kanban:** Creates a step-by-step roadmap and interactive Kanban tasks.
- **Investor & Pitching Advice:** Generates elevator pitches and investor strategies.

---

## 2. Technologies & Frameworks Used

The project is built as a monolithic web application with a strong emphasis on AI integration.

- **Backend:** Python 3 with **Flask** (Provides routing, API endpoints, and template rendering).
- **Database:** **SQLite** (Managed via the built-in `sqlite3` module. Used to persist generated analyses, metrics, and dashboards).
- **AI / LLM Integrations:**
  - **Google Gemini API** (Default model: `gemini-2.5-flash`). Used for generating business insights.
  - **Anthropic API** (Model: `claude-sonnet-5`). Supported as an alternative provider via configuration.
- **Frontend:** Vanilla HTML, CSS, and JavaScript (No heavy frameworks like React or Vue are currently used, keeping the frontend lightweight and straightforward).

---

## 3. System Architecture & Workflow

### Core Architecture
VentureAgent follows a classic Client-Server architecture with an external AI Service dependency.

1. **Client (Frontend):** The user interacts with HTML templates served by Flask. AJAX/Fetch calls are made from the frontend to the Flask backend for dynamic actions (like triggering a new idea analysis).
2. **Server (Flask Backend):** 
   - **Routes (`backend/routes/`):** Each major feature (SWOT, Kanban, Revenue, Competitors) has its own routing module. 
   - **Database (`backend/database.py`):** Handles CRUD operations. When a user submits an idea, the backend saves the generated `venture_score`, `risk_level`, and the raw AI analysis into the `idea_analyses` table.
3. **AI Service (`backend/services/ai_client.py`):** The application relies on a single-model, multi-turn approach rather than a complex multi-agent system. The `ai_client.py` module acts as a provider-agnostic wrapper. It formats prompts, enforces JSON output where necessary, and communicates securely with Gemini (or Claude) via their respective APIs.

### Data Flow Example (Idea Analysis)
1. User enters their startup idea on the frontend and clicks submit.
2. The request hits the backend route (e.g., in `backend/routes/idea.py`).
3. The route constructs a specific prompt and calls `ask_ai()` from `ai_client.py`.
4. `ai_client.py` sends the prompt to the Google Gemini API.
5. The Gemini API returns a structured response (often formatted as JSON).
6. The backend parses this response, saves the resulting metrics to the SQLite database via `save_idea_analysis()`, and returns the data to the frontend to be displayed.

---

## 4. Setup & Run Instructions

Follow these steps to spin up the project locally:

### Prerequisites
- Python 3.9+ installed.
- API keys for Google Gemini (and optionally Anthropic Claude).

### Step-by-Step Guide
1. **Clone the Repository (if you haven't already):**
   ```bash
   git clone <repository-url>
   cd VentureAgent
   ```

2. **Create a Virtual Environment:**
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows use: venv\Scripts\activate
   ```

3. **Install Dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Environment Variables:**
   - Copy the example environment file to create your own:
     ```bash
     cp .env.example .env
     ```
   - Open `.env` and fill in your API keys:
     ```env
     GEMINI_API_KEY=your_gemini_api_key_here
     ANTHROPIC_API_KEY=your_anthropic_api_key_here
     AI_PROVIDER=gemini  # or claude
     FLASK_DEBUG=True
     PORT=5000
     ```

5. **Run the Application:**
   ```bash
   python run.py
   ```
   The database tables will automatically be initialized on the first run.

6. **Access the Web App:**
   Open your browser and navigate to `http://localhost:5000`.

---

## 5. Project Structure

Here is a breakdown of the key directories and files:

```text
VentureAgent/
├── run.py                    # The entry point of the application. Starts the Flask server.
├── requirements.txt          # Python dependencies (Flask, python-dotenv, anthropic, etc.).
├── .env.example              # Template for environment variables.
├── README.md                 # Original project overview and sprint notes.
├── backend/                  # Backend application logic.
│   ├── __init__.py           # Flask app factory (create_app).
│   ├── database.py           # SQLite connection setup, schema creation, and CRUD functions.
│   ├── routes/               # Modular Flask blueprints for each feature.
│   │   ├── idea.py           # Routes for initial idea analysis.
│   │   ├── swot.py           # Routes for SWOT generation.
│   │   ├── kanban.py         # Routes for MVP task generation.
│   │   └── ...               # (competitors, revenue, roadmap, pitch, etc.)
│   └── services/
│       └── ai_client.py      # The core AI wrapper communicating with Gemini and Claude APIs.
├── frontend/                 # Frontend assets and templates.
│   ├── static/               # CSS styles, JavaScript logic, and images/logos.
│   └── templates/            # HTML files rendered by Flask.
└── data_science/             # Data analytics, notebooks, and models (e.g., exploratory notebooks, pipelines).
```
