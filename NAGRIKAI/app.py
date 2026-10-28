import os
import uuid
from flask import Flask, request, jsonify, render_template, session, send_from_directory
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv

load_dotenv()

import database
from ml_filter import moderate_text
import civic_llm

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(database.DATA_DIR, "uploads") if database.DATA_DIR != BASE_DIR else os.path.join(BASE_DIR, "static", "uploads")
ALLOWED_IMAGE_EXT = {"png", "jpg", "jpeg", "gif", "webp"}
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY") or "dev-only-change-me"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16 MB max
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"


@app.route("/static/uploads/<path:filename>")
def serve_upload(filename):
    path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    if not os.path.exists(path):  # fall back to images bundled with the app
        return send_from_directory(os.path.join(BASE_DIR, "static", "uploads"), filename)
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename)

# Initialize database on startup
database.init_db()


def get_current_user():
    user_id = session.get("user_id", 1)  # Default user
    conn = database.get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, username, avatar_url FROM users WHERE id = ?", (user_id,))
    user = cursor.fetchone()
    conn.close()
    if user:
        return dict(user)
    return {"id": 1, "name": "Anju Saxena", "username": "anju123@a", "avatar_url": "/static/assets/profile_icon.png"}


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
    data = request.get_json(silent=True) or request.form
    username = str(data.get("username", "")).strip()
    name = str(data.get("name", "")).strip() or username.split("@")[0]
    password = str(data.get("password", "")).strip()

    if not username:
        return jsonify({"success": False, "error": "Username is required."}), 400

    if not password:
        return jsonify({"success": False, "error": "Password is required."}), 400

    conn = database.get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, username, avatar_url, password FROM users WHERE username = ?", (username,))
    row = cursor.fetchone()

    if row:
        stored = row["password"]
        is_hashed = stored.startswith(("pbkdf2:", "scrypt:"))
        valid = check_password_hash(stored, password) if is_hashed else (stored == password)
        if not valid:
            conn.close()
            return jsonify({"success": False, "error": "Incorrect password for this username."}), 401
        if not is_hashed:  # upgrade legacy plaintext password to a hash
            cursor.execute("UPDATE users SET password = ? WHERE id = ?", (generate_password_hash(password), row["id"]))
            conn.commit()
        user_id = row["id"]
        user_data = {k: row[k] for k in ("id", "name", "username", "avatar_url")}
    else:
        cursor.execute("INSERT INTO users (name, username, password) VALUES (?, ?, ?)",
                       (name, username, generate_password_hash(password)))
        conn.commit()
        user_id = cursor.lastrowid
        user_data = {"id": user_id, "name": name, "username": username, "avatar_url": "/static/assets/profile_icon.png"}

    conn.close()
    session["user_id"] = user_id
    return jsonify({"success": True, "user": user_data})


@app.route("/api/logout", methods=["POST"])
def api_logout():
    session.pop("user_id", None)
    return jsonify({"success": True})


@app.route("/api/categories", methods=["GET"])
def api_categories():
    counts = database.get_category_counts()
    return jsonify(counts)


@app.route("/api/posts", methods=["GET"])
def api_get_posts():
    user = get_current_user()
    category = request.args.get("category", "All")
    search = request.args.get("search", "")
    zone = request.args.get("zone", "All")
    limit = int(request.args.get("limit", 20))
    offset = int(request.args.get("offset", 0))

    result = database.get_posts(
        category=category,
        search=search,
        zone=zone,
        limit=limit,
        offset=offset,
        user_id=user["id"]
    )
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
                ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
                if ext not in ALLOWED_IMAGE_EXT:
                    return jsonify({"success": False, "error": "Only image files (png, jpg, jpeg, gif, webp) are allowed."}), 400
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

    conn = database.get_db()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO posts (
        user_id, author_name, author_username, category, title, location,
        latitude, longitude, zone, severity, description, image_url,
        likes_count, comments_count, shares_count, ai_solution, ai_authority,
        ai_delhi_rules, solution_upvotes, solution_downvotes, resolved_status,
        moderation_score
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'Medium', ?, ?, 0, 0, 0, ?, ?, ?, 0, 0, 'Open', ?)
    """, (
        user["id"], user["name"], user["username"], category, title, location,
        lat, lng, zone, description, image_url,
        ai_res["solution"], ai_res["authority"], ai_res["rules"],
        moderation_result["score"]
    ))
    post_id = cursor.lastrowid
    conn.commit()

    cursor.execute("SELECT * FROM posts WHERE id = ?", (post_id,))
    new_post = dict(cursor.fetchone())
    new_post["user_liked"] = False
    new_post["user_solution_vote"] = None
    new_post["comments"] = []
    conn.close()

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
    conn = database.get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT id FROM post_likes WHERE post_id = ? AND user_id = ?", (post_id, user["id"]))
    existing = cursor.fetchone()

    if existing:
        cursor.execute("DELETE FROM post_likes WHERE id = ?", (existing["id"],))
        cursor.execute("UPDATE posts SET likes_count = MAX(0, likes_count - 1) WHERE id = ?", (post_id,))
        liked = False
    else:
        cursor.execute("INSERT INTO post_likes (post_id, user_id) VALUES (?, ?)", (post_id, user["id"]))
        cursor.execute("UPDATE posts SET likes_count = likes_count + 1 WHERE id = ?", (post_id,))
        liked = True

    conn.commit()
    cursor.execute("SELECT likes_count FROM posts WHERE id = ?", (post_id,))
    likes_count = cursor.fetchone()["likes_count"]
    conn.close()

    return jsonify({"success": True, "liked": liked, "likes_count": likes_count})


@app.route("/api/posts/<int:post_id>/vote-solution", methods=["POST"])
def api_vote_solution(post_id):
    """Upvote or downvote the AI-generated Delhi legal resolution."""
    user = get_current_user()
    data = request.get_json(silent=True) or request.form
    vote_type = str(data.get("vote_type", "")).strip().lower()

    if vote_type not in ("up", "down"):
        return jsonify({"success": False, "error": "Vote type must be 'up' or 'down'"}), 400

    result = database.vote_solution(post_id, user["id"], vote_type)
    return jsonify(result)


@app.route("/api/posts/<int:post_id>/ai-solve", methods=["POST"])
def api_ai_solve_post(post_id):
    """Invokes Groq LLM live to generate a fresh Delhi legal/municipal solution for this post."""
    conn = database.get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, title, description, category, location FROM posts WHERE id = ?", (post_id,))
    post = cursor.fetchone()
    conn.close()

    if not post:
        return jsonify({"success": False, "error": "Post not found"}), 404

    # Call Groq LLM
    ai_res = civic_llm.generate_delhi_ai_solution(
        title=post["title"] or post["description"][:60],
        description=post["description"],
        location=post["location"] or "Delhi",
        category=post["category"]
    )

    # Persist updated AI solution
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

    conn = database.get_db()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO post_comments (post_id, user_id, author_username, comment_text)
    VALUES (?, ?, ?, ?)
    """, (post_id, user["id"], user["username"], text))
    cursor.execute("UPDATE posts SET comments_count = comments_count + 1 WHERE id = ?", (post_id,))
    conn.commit()

    cursor.execute("SELECT id, author_username, comment_text, created_at FROM post_comments WHERE post_id = ? ORDER BY id ASC", (post_id,))
    comments = [dict(c) for c in cursor.fetchall()]
    conn.close()

    return jsonify({"success": True, "comments": comments, "comments_count": len(comments)})


@app.route("/api/statistics", methods=["GET"])
def api_statistics():
    """Returns statistical overview, most common complaints, location ranking, zone distribution, and trends."""
    stats = database.get_statistics()
    return jsonify(stats)


@app.route("/api/map-locations", methods=["GET"])
def api_map_locations():
    """Returns Delhi map locations with zone status and complaint metrics for Leaflet map."""
    locations = database.get_map_locations()
    return jsonify({"locations": locations})


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

    conn = database.get_db()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO llm_messages (session_id, user_id, role, content) VALUES (?, ?, 'user', ?)",
                   (session_id, user["id"], query))
    cursor.execute("INSERT INTO llm_messages (session_id, user_id, role, content) VALUES (?, ?, 'assistant', ?)",
                   (session_id, user["id"], result["reply"]))
    conn.commit()
    conn.close()

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

    conn = database.get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT role, content, created_at FROM llm_messages WHERE session_id = ? ORDER BY id ASC", (session_id,))
    messages = [dict(m) for m in cursor.fetchall()]
    conn.close()
    return jsonify({"messages": messages})


@app.route("/api/groq-status", methods=["GET"])
def api_groq_status():
    """Checks and returns the live connection status of Groq API."""
    status = civic_llm.test_groq_connection()
    return jsonify(status)


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "app": "NAGRIK AI", "groq_configured": bool(os.environ.get("GROQ_API_KEY"))})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=False)
