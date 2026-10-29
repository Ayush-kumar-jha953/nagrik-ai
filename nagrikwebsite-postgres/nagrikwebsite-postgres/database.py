"""
NAGRIK AI - database layer (PostgreSQL).

Same database name as before ("nagrik"), same table names, same function names.
Only the engine changed: SQLite (nagrik.db)  ->  PostgreSQL.

Connection comes from the DATABASE_URL environment variable (put it in .env):
    Local : postgresql://postgres:PASSWORD@localhost:5432/nagrik
    Neon  : postgresql://USER:PASSWORD@ep-xxxx.neon.tech/nagrik?sslmode=require
"""
import os
import threading
from datetime import datetime, date

import psycopg2
from psycopg2 import pool
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:your_password@localhost:5432/nagrik",
)

TIME_FMT = "%Y-%m-%d %H:%M:%S"   # same text format SQLite used, so the JS keeps working


# --------------------------------------------------------------------------
# Cursor that returns dict rows and turns datetimes into the old text format
# --------------------------------------------------------------------------
class NagrikCursor(RealDictCursor):
    @staticmethod
    def _fix(row):
        if row is None:
            return None
        for k, v in row.items():
            if isinstance(v, datetime):
                row[k] = v.strftime(TIME_FMT)
            elif isinstance(v, date):
                row[k] = v.isoformat()
        return row

    def fetchone(self):
        return self._fix(super().fetchone())

    def fetchall(self):
        return [self._fix(r) for r in super().fetchall()]

    def fetchmany(self, size=None):
        return [self._fix(r) for r in super().fetchmany(size)]


# --------------------------------------------------------------------------
# Small connection pool (so every request does not open a new SSL connection)
# --------------------------------------------------------------------------
_pool = None
_pool_lock = threading.Lock()


def _get_pool():
    global _pool
    with _pool_lock:
        if _pool is None:
            _pool = pool.ThreadedConnectionPool(
                1, 10, DATABASE_URL,
                cursor_factory=NagrikCursor,
                keepalives=1, keepalives_idle=30,
                keepalives_interval=10, keepalives_count=5,
                connect_timeout=15,
            )
        return _pool


class PooledConnection:
    """Behaves like the old sqlite connection: .cursor() .commit() .close()."""

    def __init__(self, raw):
        self._raw = raw

    def cursor(self):
        return self._raw.cursor()

    def commit(self):
        self._raw.commit()

    def rollback(self):
        self._raw.rollback()

    def close(self):
        # give it back to the pool (the pool rolls back anything uncommitted)
        try:
            _get_pool().putconn(self._raw)
        except Exception:
            pass


def get_db():
    """Return a connection. Same name/usage as the SQLite version."""
    p = _get_pool()
    for _ in range(3):
        raw = p.getconn()
        try:
            with raw.cursor() as cur:       # Neon sleeps when idle -> drop dead connections
                cur.execute("SELECT 1")
            raw.rollback()
            return PooledConnection(raw)
        except Exception:
            p.putconn(raw, close=True)
    raise psycopg2.OperationalError("Could not connect to PostgreSQL. Check DATABASE_URL.")


# --------------------------------------------------------------------------
# Schema (same tables and columns as the SQLite version)
# --------------------------------------------------------------------------
REQUIRED_TABLES = ["users", "posts", "post_likes", "solution_votes",
                   "post_comments", "llm_messages", "complaints"]

SCHEMA = [
    """
    CREATE TABLE IF NOT EXISTS users (
        id SERIAL PRIMARY KEY,
        name TEXT NOT NULL,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        avatar_url TEXT DEFAULT '/static/assets/profile_icon.png',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS posts (
        id SERIAL PRIMARY KEY,
        user_id INTEGER NOT NULL REFERENCES users(id),
        author_name TEXT NOT NULL,
        author_username TEXT NOT NULL,
        category TEXT NOT NULL,
        title TEXT,
        location TEXT,
        latitude DOUBLE PRECISION,
        longitude DOUBLE PRECISION,
        zone TEXT DEFAULT 'yellow',
        severity TEXT DEFAULT 'Medium',
        description TEXT NOT NULL,
        image_url TEXT,
        likes_count INTEGER DEFAULT 0,
        comments_count INTEGER DEFAULT 0,
        shares_count INTEGER DEFAULT 0,
        ai_solution TEXT,
        ai_authority TEXT,
        ai_delhi_rules TEXT,
        solution_upvotes INTEGER DEFAULT 0,
        solution_downvotes INTEGER DEFAULT 0,
        resolved_status TEXT DEFAULT 'Open',
        status TEXT DEFAULT 'approved',
        moderation_score DOUBLE PRECISION DEFAULT 0.0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS post_likes (
        id SERIAL PRIMARY KEY,
        post_id INTEGER NOT NULL REFERENCES posts(id) ON DELETE CASCADE,
        user_id INTEGER NOT NULL REFERENCES users(id),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE (post_id, user_id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS solution_votes (
        id SERIAL PRIMARY KEY,
        post_id INTEGER NOT NULL REFERENCES posts(id) ON DELETE CASCADE,
        user_id INTEGER NOT NULL REFERENCES users(id),
        vote_type TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE (post_id, user_id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS post_comments (
        id SERIAL PRIMARY KEY,
        post_id INTEGER NOT NULL REFERENCES posts(id) ON DELETE CASCADE,
        user_id INTEGER NOT NULL REFERENCES users(id),
        author_username TEXT NOT NULL,
        comment_text TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS llm_messages (
        id SERIAL PRIMARY KEY,
        session_id TEXT NOT NULL,
        user_id INTEGER,
        role TEXT NOT NULL,
        content TEXT NOT NULL,
        metadata_json TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """,
    # legacy table that existed in your old nagrik.db (kept so no data is lost)
    """
    CREATE TABLE IF NOT EXISTS complaints (
        id TEXT PRIMARY KEY,
        user_id INTEGER REFERENCES users(id),
        category TEXT NOT NULL,
        issue_type TEXT NOT NULL,
        problem TEXT NOT NULL,
        duration TEXT,
        location TEXT,
        latitude DOUBLE PRECISION,
        longitude DOUBLE PRECISION,
        suggested_action TEXT,
        authority TEXT,
        severity TEXT DEFAULT 'Medium',
        language TEXT DEFAULT 'English',
        original_text TEXT,
        images TEXT,
        status TEXT DEFAULT 'Registered',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_posts_category ON posts (category)",
    "CREATE INDEX IF NOT EXISTS idx_posts_created ON posts (created_at)",
    "CREATE INDEX IF NOT EXISTS idx_comments_post ON post_comments (post_id)",
    "CREATE INDEX IF NOT EXISTS idx_llm_session ON llm_messages (session_id)",
]


def _tables_exist(cursor):
    cursor.execute(
        "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'"
    )
    have = {r["table_name"] for r in cursor.fetchall()}
    return all(t in have for t in REQUIRED_TABLES)


def init_db():
    """Create tables if they are missing. If they all exist this does nothing,
    so the limited 'friend_app' role (which cannot CREATE) can start the app safely."""
    conn = get_db()
    cursor = conn.cursor()
    try:
        if _tables_exist(cursor):
            return
        for stmt in SCHEMA:
            cursor.execute(stmt)
        conn.commit()
    finally:
        conn.close()


# --------------------------------------------------------------------------
# Queries (same names, same return shapes as before)
# --------------------------------------------------------------------------
def get_category_counts():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT category, COUNT(*) AS count
    FROM posts
    WHERE status = 'approved'
    GROUP BY category
    """)
    rows = cursor.fetchall()
    counts = {
        "Climate Issue": 0,
        "Healthcare": 0,
        "Education": 0,
        "Sanitation": 0,
        "Infrastructure": 0
    }
    for r in rows:
        cat = r["category"]
        if cat in counts:
            counts[cat] = r["count"]
        elif cat.lower().startswith("climate"):
            counts["Climate Issue"] = r["count"]
    conn.close()
    return counts


def get_posts(category=None, search=None, zone=None, limit=50, offset=0, user_id=1):
    """Posts with optional filters. Includes user_liked and user_solution_vote."""
    conn = get_db()
    cursor = conn.cursor()

    where = " WHERE p.status = 'approved'"
    where_params = []

    if category and category.lower() != "all":
        if "climate" in category.lower():
            where += " AND (p.category = 'Climate' OR p.category = 'Climate Issue')"
        else:
            where += " AND LOWER(p.category) = LOWER(%s)"
            where_params.append(category)

    if zone and zone.lower() != "all":
        where += " AND LOWER(p.zone) = LOWER(%s)"
        where_params.append(zone)

    if search:
        sp = f"%{search.strip().lower()}%"
        where += " AND (LOWER(p.title) LIKE %s OR LOWER(p.description) LIKE %s OR LOWER(p.location) LIKE %s)"
        where_params.extend([sp, sp, sp])

    cursor.execute("SELECT COUNT(*) AS total FROM posts p" + where, where_params)
    total_matching = cursor.fetchone()["total"]

    query = """
    SELECT p.*,
           EXISTS(SELECT 1 FROM post_likes l WHERE l.post_id = p.id AND l.user_id = %s) AS user_liked,
           (SELECT vote_type FROM solution_votes sv WHERE sv.post_id = p.id AND sv.user_id = %s) AS user_solution_vote
    FROM posts p
    """ + where + " ORDER BY p.id DESC LIMIT %s OFFSET %s"
    cursor.execute(query, [user_id, user_id] + where_params + [limit, offset])
    rows = cursor.fetchall()

    posts = []
    for row in rows:
        p = dict(row)
        p["user_liked"] = bool(p["user_liked"])
        cursor.execute(
            "SELECT id, author_username, comment_text, created_at "
            "FROM post_comments WHERE post_id = %s ORDER BY id ASC", (p["id"],))
        p["comments"] = [dict(c) for c in cursor.fetchall()]
        posts.append(p)

    conn.close()
    return {"posts": posts, "total": total_matching, "limit": limit, "offset": offset}


def vote_solution(post_id, user_id, vote_type):
    """Up/down vote on the AI-generated solution. vote_type: 'up' or 'down'."""
    if vote_type not in ("up", "down"):
        return {"success": False, "error": "Invalid vote type"}

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT id FROM posts WHERE id = %s", (post_id,))
    if not cursor.fetchone():
        conn.close()
        return {"success": False, "error": "Post not found"}

    cursor.execute("SELECT id, vote_type FROM solution_votes WHERE post_id = %s AND user_id = %s",
                   (post_id, user_id))
    existing = cursor.fetchone()

    if existing:
        old_vote = existing["vote_type"]
        if old_vote == vote_type:
            cursor.execute("DELETE FROM solution_votes WHERE id = %s", (existing["id"],))
            if vote_type == "up":
                cursor.execute("UPDATE posts SET solution_upvotes = GREATEST(0, solution_upvotes - 1) WHERE id = %s", (post_id,))
            else:
                cursor.execute("UPDATE posts SET solution_downvotes = GREATEST(0, solution_downvotes - 1) WHERE id = %s", (post_id,))
            user_vote = None
        else:
            cursor.execute("UPDATE solution_votes SET vote_type = %s WHERE id = %s", (vote_type, existing["id"]))
            if vote_type == "up":
                cursor.execute("UPDATE posts SET solution_upvotes = solution_upvotes + 1, solution_downvotes = GREATEST(0, solution_downvotes - 1) WHERE id = %s", (post_id,))
            else:
                cursor.execute("UPDATE posts SET solution_downvotes = solution_downvotes + 1, solution_upvotes = GREATEST(0, solution_upvotes - 1) WHERE id = %s", (post_id,))
            user_vote = vote_type
    else:
        cursor.execute("INSERT INTO solution_votes (post_id, user_id, vote_type) VALUES (%s, %s, %s)",
                       (post_id, user_id, vote_type))
        if vote_type == "up":
            cursor.execute("UPDATE posts SET solution_upvotes = solution_upvotes + 1 WHERE id = %s", (post_id,))
        else:
            cursor.execute("UPDATE posts SET solution_downvotes = solution_downvotes + 1 WHERE id = %s", (post_id,))
        user_vote = vote_type

    conn.commit()
    cursor.execute("SELECT solution_upvotes, solution_downvotes FROM posts WHERE id = %s", (post_id,))
    row = cursor.fetchone()
    conn.close()

    return {
        "success": True,
        "solution_upvotes": row["solution_upvotes"],
        "solution_downvotes": row["solution_downvotes"],
        "user_vote": user_vote
    }


def update_post_ai_solution(post_id, ai_solution, ai_authority, ai_rules):
    """Store a fresh Groq AI solution on the post."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
    UPDATE posts
    SET ai_solution = %s, ai_authority = %s, ai_delhi_rules = %s
    WHERE id = %s
    """, (ai_solution, ai_authority, ai_rules, post_id))
    conn.commit()
    conn.close()


def get_statistics():
    """Totals, category/zone breakdown, location ranking, common issues, monthly trend."""
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) AS total FROM posts WHERE status = 'approved'")
    total_complaints = cursor.fetchone()["total"]

    cursor.execute("SELECT category, COUNT(*) AS cnt FROM posts WHERE status = 'approved' GROUP BY category")
    category_counts = {r["category"]: r["cnt"] for r in cursor.fetchall()}

    cursor.execute("SELECT zone, COUNT(*) AS cnt FROM posts WHERE status = 'approved' GROUP BY zone")
    zone_counts = {(r["zone"] or "").lower(): r["cnt"] for r in cursor.fetchall()}

    cursor.execute("""
    SELECT location, MAX(zone) AS zone, COUNT(*) AS count,
           SUM(CASE WHEN category = 'Infrastructure' THEN 1 ELSE 0 END) AS infra_cnt,
           SUM(CASE WHEN category = 'Sanitation' THEN 1 ELSE 0 END) AS sanit_cnt,
           AVG(latitude) AS lat, AVG(longitude) AS lng
    FROM posts
    WHERE status = 'approved'
    GROUP BY location
    ORDER BY COUNT(*) DESC
    LIMIT 20
    """)
    location_ranking = [dict(r) for r in cursor.fetchall()]

    problem_clusters = [
        {"issue": "Potholes & Broken Asphalt Roads", "category": "Infrastructure", "count": 0},
        {"issue": "Overflowing Garbage Dhalaos & Dumping", "category": "Sanitation", "count": 0},
        {"issue": "Dark Streets & Non-functional Streetlights", "category": "Infrastructure", "count": 0},
        {"issue": "Choked Stormwater Drains & Sewage Backflow", "category": "Sanitation", "count": 0},
        {"issue": "School Infrastructure & Missing Desks", "category": "Education", "count": 0},
        {"issue": "Primary Health Medicine Stockouts", "category": "Healthcare", "count": 0},
        {"issue": "Road Dust & Uncovered Construction Debris", "category": "Climate", "count": 0},
        {"issue": "Potable Water Pipeline Ruptures & Leaks", "category": "Infrastructure", "count": 0},
        {"issue": "Open Biomass & Leaf Burning (GRAP Violations)", "category": "Climate", "count": 0},
        {"issue": "Hospital Diagnostic Machinery Downtime", "category": "Healthcare", "count": 0}
    ]

    for cluster in problem_clusters:
        words = cluster["issue"].split()
        first_word = words[0].lower()
        second_word = words[1].lower() if len(words) > 1 else ""
        cursor.execute("""
        SELECT COUNT(*) AS cnt FROM posts
        WHERE status = 'approved'
          AND (LOWER(title) LIKE %s OR LOWER(title) LIKE %s OR LOWER(description) LIKE %s)
        """, (f"%{first_word}%", f"%{second_word}%", f"%{first_word}%"))
        cluster["count"] = max(cursor.fetchone()["cnt"], 18)

    problem_clusters.sort(key=lambda x: x["count"], reverse=True)

    cursor.execute("""
    SELECT to_char(created_at, 'YYYY-MM') AS month,
           COUNT(*) AS total,
           SUM(CASE WHEN category = 'Infrastructure' THEN 1 ELSE 0 END) AS infrastructure,
           SUM(CASE WHEN category = 'Sanitation' THEN 1 ELSE 0 END) AS sanitation,
           SUM(CASE WHEN category = 'Education' THEN 1 ELSE 0 END) AS education,
           SUM(CASE WHEN category = 'Healthcare' THEN 1 ELSE 0 END) AS healthcare,
           SUM(CASE WHEN category = 'Climate' OR category = 'Climate Issue' THEN 1 ELSE 0 END) AS climate,
           SUM(CASE WHEN resolved_status = 'Resolved' OR resolved_status = 'Action Taken' THEN 1 ELSE 0 END) AS resolved
    FROM posts
    WHERE status = 'approved'
    GROUP BY 1
    ORDER BY 1 ASC
    """)
    trend_rows = [dict(r) for r in cursor.fetchall()]

    conn.close()

    return {
        "total_complaints": total_complaints,
        "category_counts": category_counts,
        "zone_counts": {
            "red": zone_counts.get("red", 0),
            "yellow": zone_counts.get("yellow", 0),
            "green": zone_counts.get("green", 0)
        },
        "location_ranking": location_ranking,
        "problem_clusters": problem_clusters,
        "trend_data": trend_rows
    }


def get_map_locations():
    """Aggregated Delhi map locations for the Leaflet map."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT location, MAX(zone) AS zone, COUNT(*) AS count,
           AVG(latitude) AS lat, AVG(longitude) AS lng,
           SUM(CASE WHEN category = 'Infrastructure' THEN 1 ELSE 0 END) AS infra_count,
           SUM(CASE WHEN category = 'Sanitation' THEN 1 ELSE 0 END) AS sanit_count,
           SUM(CASE WHEN category = 'Education' THEN 1 ELSE 0 END) AS edu_count,
           SUM(CASE WHEN category = 'Healthcare' THEN 1 ELSE 0 END) AS health_count,
           SUM(CASE WHEN category = 'Climate' OR category = 'Climate Issue' THEN 1 ELSE 0 END) AS climate_count
    FROM posts
    WHERE status = 'approved' AND latitude IS NOT NULL AND longitude IS NOT NULL
    GROUP BY location
    ORDER BY COUNT(*) DESC
    """)
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows


# --------------------------------------------------------------------------
# Helpers used by app.py (users, posts, likes, comments, chat history)
# --------------------------------------------------------------------------
def get_user_by_id(user_id):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT id, name, username, avatar_url FROM users WHERE id = %s", (user_id,))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None


def get_user_for_login(username):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT id, name, username, password, avatar_url FROM users WHERE username = %s", (username,))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None


def create_user(name, username, password_hash):
    """Insert a user. Returns the new row, or None if the username is already taken."""
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO users (name, username, password) VALUES (%s, %s, %s) "
        "ON CONFLICT (username) DO NOTHING "
        "RETURNING id, name, username, avatar_url",
        (name, username, password_hash))
    row = cur.fetchone()
    conn.commit()
    conn.close()
    return dict(row) if row else None


def set_user_password(user_id, password_hash):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("UPDATE users SET password = %s WHERE id = %s", (password_hash, user_id))
    conn.commit()
    conn.close()


def create_post(user, category, title, location, lat, lng, zone, description,
                image_url, ai_res, moderation_score):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
    INSERT INTO posts (
        user_id, author_name, author_username, category, title, location,
        latitude, longitude, zone, severity, description, image_url,
        likes_count, comments_count, shares_count, ai_solution, ai_authority,
        ai_delhi_rules, solution_upvotes, solution_downvotes, resolved_status,
        moderation_score
    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 'Medium', %s, %s, 0, 0, 0, %s, %s, %s, 0, 0, 'Open', %s)
    RETURNING *
    """, (
        user["id"], user["name"], user["username"], category, title, location,
        lat, lng, zone, description, image_url,
        ai_res["solution"], ai_res["authority"], ai_res["rules"], moderation_score
    ))
    new_post = dict(cur.fetchone())
    conn.commit()
    conn.close()
    new_post["user_liked"] = False
    new_post["user_solution_vote"] = None
    new_post["comments"] = []
    return new_post


def toggle_like(post_id, user_id):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT id FROM posts WHERE id = %s", (post_id,))
    if not cur.fetchone():
        conn.close()
        return None
    cur.execute("SELECT id FROM post_likes WHERE post_id = %s AND user_id = %s", (post_id, user_id))
    existing = cur.fetchone()
    if existing:
        cur.execute("DELETE FROM post_likes WHERE id = %s", (existing["id"],))
        cur.execute("UPDATE posts SET likes_count = GREATEST(0, likes_count - 1) WHERE id = %s", (post_id,))
        liked = False
    else:
        cur.execute("INSERT INTO post_likes (post_id, user_id) VALUES (%s, %s)", (post_id, user_id))
        cur.execute("UPDATE posts SET likes_count = likes_count + 1 WHERE id = %s", (post_id,))
        liked = True
    conn.commit()
    cur.execute("SELECT likes_count FROM posts WHERE id = %s", (post_id,))
    likes_count = cur.fetchone()["likes_count"]
    conn.close()
    return {"liked": liked, "likes_count": likes_count}


def add_comment(post_id, user_id, username, text):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT id FROM posts WHERE id = %s", (post_id,))
    if not cur.fetchone():
        conn.close()
        return None
    cur.execute(
        "INSERT INTO post_comments (post_id, user_id, author_username, comment_text) VALUES (%s, %s, %s, %s)",
        (post_id, user_id, username, text))
    cur.execute("UPDATE posts SET comments_count = comments_count + 1 WHERE id = %s", (post_id,))
    conn.commit()
    cur.execute(
        "SELECT id, author_username, comment_text, created_at FROM post_comments "
        "WHERE post_id = %s ORDER BY id ASC", (post_id,))
    comments = [dict(c) for c in cur.fetchall()]
    conn.close()
    return comments


def get_post_basic(post_id):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT id, title, description, category, location FROM posts WHERE id = %s", (post_id,))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None


def save_chat_pair(session_id, user_id, query, reply):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("INSERT INTO llm_messages (session_id, user_id, role, content) VALUES (%s, %s, 'user', %s)",
                (session_id, user_id, query))
    cur.execute("INSERT INTO llm_messages (session_id, user_id, role, content) VALUES (%s, %s, 'assistant', %s)",
                (session_id, user_id, reply))
    conn.commit()
    conn.close()


def get_chat_history(session_id):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT role, content, created_at FROM llm_messages WHERE session_id = %s ORDER BY id ASC",
                (session_id,))
    msgs = [dict(m) for m in cur.fetchall()]
    conn.close()
    return msgs
