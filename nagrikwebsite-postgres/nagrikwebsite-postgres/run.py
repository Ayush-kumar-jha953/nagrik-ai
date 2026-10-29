"""NAGRIK AI - Application Runner
Launches the Flask web server on http://127.0.0.1:5000
"""
import os
import sys
import logging

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app
import database

if __name__ == "__main__":
    database.init_db()

    log = logging.getLogger('werkzeug')
    log.setLevel(logging.ERROR)

    print("=" * 65, flush=True)
    print("   NAGRIK AI - Civic Problem Platform & AI Assistant", flush=True)
    print("   Backend: PostgreSQL (database: nagrik)", flush=True)
    print("   ML Moderation: UPKAR-ML (LinearSVC & Preprocessing)", flush=True)
    print("   AI Assistant: Groq LLM (Delhi Municipal Rules Engine)", flush=True)
    print("=" * 65, flush=True)
    print("   Server running at: http://127.0.0.1:5000", flush=True)
    print("   Open your browser and navigate to the link above.", flush=True)
    print("=" * 65, flush=True)

    app.run(host="127.0.0.1", port=5000, debug=False, use_reloader=False)
