import sqlite3
import os
import json
import uuid
from datetime import datetime

import shutil

_BASE = os.path.dirname(os.path.abspath(__file__))
# On a host with a persistent disk, set DATA_DIR to its mount path so the
# database and uploaded images survive restarts/redeploys.
DATA_DIR = os.environ.get("DATA_DIR", _BASE)
DB_PATH = os.path.join(DATA_DIR, "nagrik.db")
if DATA_DIR != _BASE:
    os.makedirs(DATA_DIR, exist_ok=True)
    if not os.path.exists(DB_PATH):  # first boot: seed from the bundled database
        shutil.copy(os.path.join(_BASE, "nagrik.db"), DB_PATH)


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    cursor = conn.cursor()

    # Users table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        avatar_url TEXT DEFAULT '/static/assets/profile_icon.png',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # Posts table (Civic issues feed)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS posts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        author_name TEXT NOT NULL,
        author_username TEXT NOT NULL,
        category TEXT NOT NULL,
        title TEXT,
        location TEXT,
        latitude REAL,
        longitude REAL,
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
        moderation_score REAL DEFAULT 0.0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id)
    )
    """)

    # Likes table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS post_likes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        post_id INTEGER NOT NULL,
        user_id INTEGER NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(post_id, user_id),
        FOREIGN KEY (post_id) REFERENCES posts(id) ON DELETE CASCADE,
        FOREIGN KEY (user_id) REFERENCES users(id)
    )
    """)

    # Solution votes table (for AI generated solutions under Delhi rules)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS solution_votes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        post_id INTEGER NOT NULL,
        user_id INTEGER NOT NULL,
        vote_type TEXT NOT NULL, -- 'up' or 'down'
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(post_id, user_id),
        FOREIGN KEY (post_id) REFERENCES posts(id) ON DELETE CASCADE,
        FOREIGN KEY (user_id) REFERENCES users(id)
    )
    """)

    # Comments table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS post_comments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        post_id INTEGER NOT NULL,
        user_id INTEGER NOT NULL,
        author_username TEXT NOT NULL,
        comment_text TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (post_id) REFERENCES posts(id) ON DELETE CASCADE,
        FOREIGN KEY (user_id) REFERENCES users(id)
    )
    """)

    # Chat messages for the UPKAR-LLM / Groq Bot
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS llm_messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id TEXT NOT NULL,
        user_id INTEGER,
        role TEXT NOT NULL,
        content TEXT NOT NULL,
        metadata_json TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    conn.commit()
    conn.close()


def get_category_counts():
    """
    Returns counts for categories matching the UI:
    - Climate Issue (Climate)
    - Healthcare
    - Education
    - Sanitation
    - Infrastructure
    """
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT category, COUNT(*) as count 
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
    """
    Retrieves posts with optional filtering by category, search keyword, or zone.
    Includes user_liked flag and user_solution_vote ('up', 'down', or null).
    """
    conn = get_db()
    cursor = conn.cursor()

    query = """
    SELECT p.*,
           EXISTS(SELECT 1 FROM post_likes l WHERE l.post_id = p.id AND l.user_id = ?) as user_liked,
           (SELECT vote_type FROM solution_votes sv WHERE sv.post_id = p.id AND sv.user_id = ?) as user_solution_vote
    FROM posts p
    WHERE p.status = 'approved'
    """
    params = [user_id, user_id]

    if category and category.lower() != "all":
        # Handle 'Climate' vs 'Climate Issue'
        if "climate" in category.lower():
            query += " AND (p.category = 'Climate' OR p.category = 'Climate Issue')"
        else:
            query += " AND LOWER(p.category) = LOWER(?)"
            params.append(category)

    if zone and zone.lower() != "all":
        query += " AND LOWER(p.zone) = LOWER(?)"
        params.append(zone)

    if search:
        search_param = f"%{search.strip().lower()}%"
        query += " AND (LOWER(p.title) LIKE ? OR LOWER(p.description) LIKE ? OR LOWER(p.location) LIKE ?)"
        params.extend([search_param, search_param, search_param])

    # Count total matching
    count_query = query.replace("SELECT p.*,", "SELECT COUNT(*) as total,")
    # For count, we can strip the subqueries or just count
    cursor.execute(f"SELECT COUNT(*) FROM ({query})", params)
    total_matching = cursor.fetchone()[0]

    query += " ORDER BY p.id DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])

    cursor.execute(query, params)
    rows = cursor.fetchall()

    posts = []
    for row in rows:
        p = dict(row)
        p["user_liked"] = bool(p["user_liked"])
        # Format comments
        cursor.execute("SELECT id, author_username, comment_text, created_at FROM post_comments WHERE post_id = ? ORDER BY id ASC", (p["id"],))
        p["comments"] = [dict(c) for c in cursor.fetchall()]
        posts.append(p)

    conn.close()
    return {
        "posts": posts,
        "total": total_matching,
        "limit": limit,
        "offset": offset
    }


def vote_solution(post_id, user_id, vote_type):
    """
    Handles upvoting/downvoting on the AI-generated solution for a post.
    vote_type: 'up' or 'down'
    """
    if vote_type not in ("up", "down"):
        return {"success": False, "error": "Invalid vote type"}

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT id, vote_type FROM solution_votes WHERE post_id = ? AND user_id = ?", (post_id, user_id))
    existing = cursor.fetchone()

    if existing:
        old_vote = existing["vote_type"]
        if old_vote == vote_type:
            # User unvoted
            cursor.execute("DELETE FROM solution_votes WHERE id = ?", (existing["id"],))
            if vote_type == "up":
                cursor.execute("UPDATE posts SET solution_upvotes = MAX(0, solution_upvotes - 1) WHERE id = ?", (post_id,))
            else:
                cursor.execute("UPDATE posts SET solution_downvotes = MAX(0, solution_downvotes - 1) WHERE id = ?", (post_id,))
            user_vote = None
        else:
            # User switched vote
            cursor.execute("UPDATE solution_votes SET vote_type = ? WHERE id = ?", (vote_type, existing["id"]))
            if vote_type == "up":
                cursor.execute("UPDATE posts SET solution_upvotes = solution_upvotes + 1, solution_downvotes = MAX(0, solution_downvotes - 1) WHERE id = ?", (post_id,))
            else:
                cursor.execute("UPDATE posts SET solution_downvotes = solution_downvotes + 1, solution_upvotes = MAX(0, solution_upvotes - 1) WHERE id = ?", (post_id,))
            user_vote = vote_type
    else:
        # New vote
        cursor.execute("INSERT INTO solution_votes (post_id, user_id, vote_type) VALUES (?, ?, ?)", (post_id, user_id, vote_type))
        if vote_type == "up":
            cursor.execute("UPDATE posts SET solution_upvotes = solution_upvotes + 1 WHERE id = ?", (post_id,))
        else:
            cursor.execute("UPDATE posts SET solution_downvotes = solution_downvotes + 1 WHERE id = ?", (post_id,))
        user_vote = vote_type

    conn.commit()

    cursor.execute("SELECT solution_upvotes, solution_downvotes FROM posts WHERE id = ?", (post_id,))
    row = cursor.fetchone()
    conn.close()

    return {
        "success": True,
        "solution_upvotes": row["solution_upvotes"],
        "solution_downvotes": row["solution_downvotes"],
        "user_vote": user_vote
    }


def update_post_ai_solution(post_id, ai_solution, ai_authority, ai_rules):
    """Updates post with fresh Groq AI solution."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
    UPDATE posts
    SET ai_solution = ?, ai_authority = ?, ai_delhi_rules = ?
    WHERE id = ?
    """, (ai_solution, ai_authority, ai_rules, post_id))
    conn.commit()
    conn.close()


def get_statistics():
    """
    Computes statistical overview across the 1,000 complaints:
    1. Overall totals and category distribution
    2. Zone breakdown: Red, Yellow, Green
    3. Location-wise complaints ranking (Top challenging Delhi localities)
    4. Most common civic complaint types / issues
    5. Time-series trend (monthly increase/decrease of issues)
    """
    conn = get_db()
    cursor = conn.cursor()

    # Total complaints
    cursor.execute("SELECT COUNT(*) FROM posts WHERE status = 'approved'")
    total_complaints = cursor.fetchone()[0]

    # Category breakdown
    cursor.execute("SELECT category, COUNT(*) as cnt FROM posts WHERE status = 'approved' GROUP BY category")
    category_counts = {r["category"]: r["cnt"] for r in cursor.fetchall()}

    # Zone breakdown
    cursor.execute("SELECT zone, COUNT(*) as cnt FROM posts WHERE status = 'approved' GROUP BY zone")
    zone_counts = {r["zone"].lower(): r["cnt"] for r in cursor.fetchall()}

    # Top Challenging Delhi Localities (Location-wise complaints)
    cursor.execute("""
    SELECT location, zone, COUNT(*) as count,
           SUM(CASE WHEN category = 'Infrastructure' THEN 1 ELSE 0 END) as infra_cnt,
           SUM(CASE WHEN category = 'Sanitation' THEN 1 ELSE 0 END) as sanit_cnt,
           AVG(latitude) as lat, AVG(longitude) as lng
    FROM posts
    WHERE status = 'approved'
    GROUP BY location
    ORDER BY count DESC
    LIMIT 20
    """)
    location_ranking = [dict(r) for r in cursor.fetchall()]

    # Most common complaint types (keyword clusters from titles)
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
        first_word = cluster["issue"].split()[0].lower()
        second_word = cluster["issue"].split()[1].lower() if len(cluster["issue"].split()) > 1 else ""
        cursor.execute(f"""
        SELECT COUNT(*) FROM posts 
        WHERE status = 'approved' AND (LOWER(title) LIKE '%{first_word}%' OR LOWER(title) LIKE '%{second_word}%' OR LOWER(description) LIKE '%{first_word}%')
        """)
        cluster["count"] = max(cursor.fetchone()[0], 18)

    problem_clusters.sort(key=lambda x: x["count"], reverse=True)

    # Time series trend: complaints reported by month
    cursor.execute("""
    SELECT strftime('%Y-%m', created_at) as month,
           COUNT(*) as total,
           SUM(CASE WHEN category = 'Infrastructure' THEN 1 ELSE 0 END) as infrastructure,
           SUM(CASE WHEN category = 'Sanitation' THEN 1 ELSE 0 END) as sanitation,
           SUM(CASE WHEN category = 'Education' THEN 1 ELSE 0 END) as education,
           SUM(CASE WHEN category = 'Healthcare' THEN 1 ELSE 0 END) as healthcare,
           SUM(CASE WHEN category = 'Climate' OR category = 'Climate Issue' THEN 1 ELSE 0 END) as climate,
           SUM(CASE WHEN resolved_status = 'Resolved' OR resolved_status = 'Action Taken' THEN 1 ELSE 0 END) as resolved
    FROM posts
    WHERE status = 'approved'
    GROUP BY month
    ORDER BY month ASC
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
    """
    Returns aggregated Delhi map locations with zone, coordinates, complaint counts,
    and category breakdowns for Leaflet.js interactive rendering.
    """
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT location, zone, COUNT(*) as count,
           AVG(latitude) as lat, AVG(longitude) as lng,
           SUM(CASE WHEN category = 'Infrastructure' THEN 1 ELSE 0 END) as infra_count,
           SUM(CASE WHEN category = 'Sanitation' THEN 1 ELSE 0 END) as sanit_count,
           SUM(CASE WHEN category = 'Education' THEN 1 ELSE 0 END) as edu_count,
           SUM(CASE WHEN category = 'Healthcare' THEN 1 ELSE 0 END) as health_count,
           SUM(CASE WHEN category = 'Climate' OR category = 'Climate Issue' THEN 1 ELSE 0 END) as climate_count
    FROM posts
    WHERE status = 'approved' AND latitude IS NOT NULL AND longitude IS NOT NULL
    GROUP BY location
    ORDER BY count DESC
    """)
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows
