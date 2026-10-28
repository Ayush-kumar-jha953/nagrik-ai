"""NAGRIK AI - Application Runner
Launches the Flask web server on http://127.0.0.1:5000
"""
import os
import sys
import logging

# Ensure current directory is on python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app
import database

if __name__ == "__main__":
    database.init_db()

    # Suppress duplicate werkzeug startup logs so the link appears strictly once
    log = logging.getLogger('werkzeug')
    log.setLevel(logging.ERROR)

    print("=" * 65, flush=True)
    print("   NAGRIK AI - Civic Problem Platform & AI Assistant", flush=True)
    print("   Backend: SQLite (nagrik.db)", flush=True)
    print("   ML Moderation: UPKAR-ML (LinearSVC & Preprocessing)", flush=True)
    print("   AI Assistant: Groq LLM (Delhi Municipal Rules Engine)", flush=True)
    print("=" * 65, flush=True)
    print("   Server running at: http://127.0.0.1:5000", flush=True)
    print("   Open your browser and navigate to the link above.", flush=True)
    print("=" * 65, flush=True)

    # use_reloader=False and debug=False prevents duplicate process creation and duplicate links
    app.run(host=os.environ.get("HOST", "127.0.0.1"), port=int(os.environ.get("PORT", 5000)), debug=False, use_reloader=False)
