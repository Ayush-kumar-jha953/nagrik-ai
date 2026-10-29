import os
import uuid
import hmac
from datetime import timedelta

from flask import Flask, request, jsonify, render_template, session, redirect, url_for
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv

load_dotenv()

import database
from ml_filter import moderate_text
import civic_llm

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, "static", "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app = Flask(__name__)
# Put SECRET_KEY in .env (any long random text). Old value kept only as a fallback.
app.secret_key = os.getenv("SECRET_KEY", "nagrik-ai-secret-session-key-2026")
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16 MB max
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(days=7)

# Create tables on startup (does nothing if they already exist)
database.init_db()

# Pages/endpoints that can be opened WITHOUT logging in
PUBLIC_ENDPOINTS = {"login_page", "api_login", "static", "health"}


# --------------------------------------------------------------------------
# Login gate: every page and API needs a logged-in user, except the list above
# --------------------------------------------------------------------------
@app.before_request
def require_login():
    if request.endpoint is None or request.endpoint in PUBLIC_ENDPOINTS:
        return None
    user_id = session.get("user_id")
    if user_id and database.get_user_by_id(user_id):
        return None
    session.pop("user_id", None)
    if request.path.startswith("/api/"):
        return jsonify({"success": False, "login_required": True,
                        "error": "Please log in first."}), 401
    return redirect(url_for("login_page"))


def get_current_user():
    return database.get_user_by_id(session.get("user_id"))


def _password_ok(stored, given):
    """Works with hashed passwords and with the old plain-text ones in the SQLite data."""
    if stored.startswith(("scrypt:", "pbkdf2:")):
        return check_password_hash(stored, given)
    return hmac.compare_digest(stored.encode(), given.encode())


# --------------------------------------------------------------------------
# Pages + auth
# --------------------------------------------------------------------------
@app.route("/login")
def login_page():
    if session.get("user_id") and database.get_user_by_id(session["user_id"]):
        return redirect(url_for("index"))
    return render_template("login.html")


@app.route("/")
def index():
    user = get_current_user()
    return render_template("index.html", user=user)


@app.route("/api/session", methods=["GET"])
def api_session():
    user = get_current_user()
    return jsonify({"authenticated": True, "user": user})


@app.route("/api/login", methods=["POST"])
def api_login():
    """Sign in. A username that does not exist yet is registered on the spot (same as before)."""
    data = request.get_json(silent=True) or request.form
    username = str(data.get("username", "")).strip()
    name = str(data.get("name", "")).strip() or username.split("@")[0]
    password = str(data.get("password", "")).strip()

    if not username:
        return jsonify({"success": False, "error": "Username is required."}), 400
    if not password:
        return jsonify({"success": False, "error": "Password is required."}), 400

    row = database.get_user_for_login(username)
    if row:
        if not _password_ok(row["password"], password):
            return jsonify({"success": False, "error": "Wrong password for this username."}), 401
        if not row["password"].startswith(("scrypt:", "pbkdf2:")):
            database.set_user_password(row["id"], generate_password_hash(password))  # upgrade old plain text
        user_data = {k: row[k] for k in ("id", "name", "username", "avatar_url")}
    else:
        user_data = database.create_user(name, username, generate_password_hash(password))
        if not user_data:
            return jsonify({"success": False, "error": "Username already taken."}), 409

    session.clear()
    session["user_id"] = user_data["id"]
    session.permanent = True
    return jsonify({"success": True, "user": user_data})


@app.route("/api/logout", methods=["POST"])
def api_logout():
    session.clear()
    return jsonify({"success": True})


@app.route("/logout")
def logout_page():
    session.clear()
    return redirect(url_for("login_page"))


# --------------------------------------------------------------------------
# Feed
# --------------------------------------------------------------------------
@app.route("/api/categories", methods=["GET"])
def api_categories():
    return jsonify(database.get_category_counts())


@app.route("/api/posts", methods=["GET"])
def api_get_posts():
    user = get_current_user()
    category = request.args.get("category", "All")
    search = request.args.get("search", "")
    zone = request.args.get("zone", "All")
    try:
        limit = max(1, min(int(request.args.get("limit", 20)), 100))
        offset = max(0, int(request.args.get("offset", 0)))
    except ValueError:
        return jsonify({"success": False, "error": "limit and offset must be numbers."}), 400

    result = database.get_posts(category=category, search=search, zone=zone,
                                limit=limit, offset=offset, user_id=user["id"])
    return jsonify(result)


@app.route("/api/posts", methods=["POST"])
def api_create_post():
    user = get_current_user()

    if request.is_json:
        data = request.get_json() or {}
        category = str(data.get("category", "Infrastructure")).strip()
        title = str(data.get("title", "")).strip()
        description = str(data.get("description", "")).strip()
        location = str(data.get("location", "New Delhi")).strip()
        image_url = data.get("image_url", "")
    else:
        category = str(request.form.get("category", "Infrastructure")).strip()
        title = str(request.form.get("title", "")).strip()
        description = str(request.form.get("description", "")).strip()
        location = str(request.form.get("location", "New Delhi")).strip()
        image_url = request.form.get("image_url", "")

        if "image_file" in request.files:
            file = request.files["image_file"]
            if file and file.filename != "":
                filename = f"{uuid.uuid4().hex[:10]}_{secure_filename(file.filename)}"
                save_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
                file.save(save_path)
                image_url = f"/static/uploads/{filename}"

    if not title:
        title = description[:60] + "..." if len(description) > 60 else description

    if not image_url:
        if category == "Sanitation":
            image_url = "/static/assets/post_garbage.png"
        elif category == "Infrastructure":
            image_url = "/static/assets/post_pothole.png"
        elif category == "Education":
            image_url = "/static/assets/post_education.jpg"
        elif category == "Healthcare":
            image_url = "/static/assets/post_healthcare.jpg"
        else:
            image_url = "/static/assets/post_climate.jpg"

    # Moderate text with UPKAR-ML
    moderation_result = moderate_text(f"{title} {description}")
    if moderation_result["flagged"]:
        return jsonify({
            "success": False,
            "flagged": True,
            "message": moderation_result["message"],
            "reason": moderation_result["reason"]
        }), 422

    # Generate Delhi-specific AI solution via Groq LLM
    ai_res = civic_llm.generate_delhi_ai_solution(title, description, location, category)

    # Determine zone
    loc_lower = location.lower()
    if any(k in loc_lower for k in ["okhla", "seelampur", "uttam nagar", "jahangirpuri", "shahdara", "burari", "najafgarh", "sangam vihar"]):
        zone = "red"
        lat, lng = 28.5307, 77.2713
    elif any(k in loc_lower for k in ["connaught", "chanakyapuri", "vasant vihar", "civil lines", "greater kailash", "model town"]):
        zone = "green"
        lat, lng = 28.6315, 77.2167
    else:
        zone = "yellow"
        lat, lng = 28.5677, 77.2433

    new_post = database.create_post(user, category, title, location, lat, lng, zone,
                                    description, image_url, ai_res, moderation_result["score"])

    return jsonify({
        "success": True,
        "flagged": False,
        "message": "Civic complaint registered and AI legal solution generated under Delhi rules!",
        "post": new_post,
        "category_counts": database.get_category_counts()
    }), 201


@app.route("/api/posts/<int:post_id>/like", methods=["POST"])
def api_toggle_like(post_id):
    user = get_current_user()
    result = database.toggle_like(post_id, user["id"])
    if result is None:
        return jsonify({"success": False, "error": "Post not found"}), 404
    return jsonify({"success": True, **result})


@app.route("/api/posts/<int:post_id>/vote-solution", methods=["POST"])
def api_vote_solution(post_id):
    """Upvote or downvote the AI-generated Delhi legal resolution."""
    user = get_current_user()
    data = request.get_json(silent=True) or request.form
    vote_type = str(data.get("vote_type", "")).strip().lower()

    if vote_type not in ("up", "down"):
        return jsonify({"success": False, "error": "Vote type must be 'up' or 'down'"}), 400

    result = database.vote_solution(post_id, user["id"], vote_type)
    if not result.get("success") and result.get("error") == "Post not found":
        return jsonify(result), 404
    return jsonify(result)


@app.route("/api/posts/<int:post_id>/ai-solve", methods=["POST"])
def api_ai_solve_post(post_id):
    """Invokes Groq LLM live to generate a fresh Delhi legal/municipal solution for this post."""
    post = database.get_post_basic(post_id)
    if not post:
        return jsonify({"success": False, "error": "Post not found"}), 404

    ai_res = civic_llm.generate_delhi_ai_solution(
        title=post["title"] or post["description"][:60],
        description=post["description"],
        location=post["location"] or "Delhi",
        category=post["category"]
    )

    database.update_post_ai_solution(post_id, ai_res["solution"], ai_res["authority"], ai_res["rules"])

    return jsonify({
        "success": True,
        "ai_solution": ai_res["solution"],
        "ai_authority": ai_res["authority"],
        "ai_delhi_rules": ai_res["rules"],
        "sla": ai_res.get("sla", "48-72 hours")
    })


@app.route("/api/posts/<int:post_id>/comment", methods=["POST"])
def api_add_comment(post_id):
    user = get_current_user()
    data = request.get_json(silent=True) or request.form
    text = str(data.get("comment", "")).strip()

    if not text:
        return jsonify({"success": False, "error": "Comment text cannot be empty."}), 400

    mod = moderate_text(text)
    if mod["flagged"]:
        return jsonify({
            "success": False,
            "flagged": True,
            "message": "Your comment cannot be posted due to inappropriate language."
        }), 422

    comments = database.add_comment(post_id, user["id"], user["username"], text)
    if comments is None:
        return jsonify({"success": False, "error": "Post not found"}), 404
    return jsonify({"success": True, "comments": comments, "comments_count": len(comments)})


@app.route("/api/statistics", methods=["GET"])
def api_statistics():
    """Statistical overview, most common complaints, location ranking, zone distribution, trends."""
    return jsonify(database.get_statistics())


@app.route("/api/map-locations", methods=["GET"])
def api_map_locations():
    """Delhi map locations with zone status and complaint metrics for the Leaflet map."""
    return jsonify({"locations": database.get_map_locations()})


# --------------------------------------------------------------------------
# AI assistant (Groq)
# --------------------------------------------------------------------------
@app.route("/api/chat", methods=["POST"])
def api_chat():
    user = get_current_user()
    data = request.get_json(silent=True) or request.form
    query = str(data.get("message", "")).strip()
    session_id = str(data.get("session_id", session.get("chat_session_id", str(uuid.uuid4()))))
    session["chat_session_id"] = session_id

    if not query:
        return jsonify({"success": False, "error": "Please enter a message."}), 400

    result = civic_llm.query_assistant(query, user_id=user["id"], session_id=session_id)
    database.save_chat_pair(session_id, user["id"], query, result["reply"])

    return jsonify({
        "success": True,
        "reply": result["reply"],
        "type": result["type"],
        "model": result.get("model", "groq"),
        "session_id": session_id
    })


@app.route("/api/chat/history", methods=["GET"])
def api_chat_history():
    session_id = request.args.get("session_id", session.get("chat_session_id", ""))
    if not session_id:
        return jsonify({"messages": []})
    return jsonify({"messages": database.get_chat_history(session_id)})


@app.route("/api/groq-status", methods=["GET"])
def api_groq_status():
    """Live connection status of the Groq API."""
    return jsonify(civic_llm.test_groq_connection())


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "app": "NAGRIK AI", "database": "postgresql", "groq_integrated": True})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
