"""
Copies ALL your old data from nagrik.db (SQLite) into PostgreSQL.
Keeps the same ids, so likes / comments / votes still point to the right posts.

    python migrate_sqlite_to_postgres.py                 # reads ./nagrik.db
    python migrate_sqlite_to_postgres.py path/to/nagrik.db
    python migrate_sqlite_to_postgres.py --force         # wipe PostgreSQL tables first

Use the OWNER connection string in DATABASE_URL.
"""
import os
import sys
import sqlite3

from psycopg2.extras import execute_values

import database

ORDER = ["users", "posts", "post_likes", "solution_votes",
         "post_comments", "llm_messages", "complaints"]
SERIAL_TABLES = [t for t in ORDER if t != "complaints"]


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    force = "--force" in sys.argv
    here = os.path.dirname(os.path.abspath(__file__))
    path = args[0] if args else os.path.join(here, "nagrik.db")
    if not os.path.exists(path):
        sys.exit(f"SQLite file not found: {path}")

    database.init_db()
    src = sqlite3.connect(path)
    src.row_factory = sqlite3.Row
    conn = database.get_db()
    cur = conn.cursor()

    cur.execute("SELECT (SELECT COUNT(*) FROM users) AS u, (SELECT COUNT(*) FROM posts) AS p")
    have = cur.fetchone()
    if (have["u"] or have["p"]) and not force:
        sys.exit("PostgreSQL already has data. Re-run with --force to wipe it and copy again.")
    if force:
        cur.execute("TRUNCATE " + ", ".join(ORDER) + " RESTART IDENTITY CASCADE")

    existing = {r[0] for r in src.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    for table in ORDER:
        if table not in existing:
            print(f"  {table}: not in SQLite file, skipped")
            continue
        cur.execute("SELECT column_name FROM information_schema.columns "
                    "WHERE table_schema='public' AND table_name=%s", (table,))
        pg_cols = {r["column_name"] for r in cur.fetchall()}
        rows = src.execute(f"SELECT * FROM {table}").fetchall()
        if not rows:
            print(f"  {table}: 0 rows")
            continue
        cols = [c for c in rows[0].keys() if c in pg_cols]
        data = [tuple(r[c] for c in cols) for r in rows]
        execute_values(cur, f"INSERT INTO {table} ({', '.join(cols)}) VALUES %s", data, page_size=500)
        print(f"  {table}: {len(data)} rows copied")

    # move the auto-number counters past the copied ids
    for table in SERIAL_TABLES:
        cur.execute(f"SELECT setval(pg_get_serial_sequence('{table}', 'id'), "
                    f"COALESCE((SELECT MAX(id) FROM {table}), 0) + 1, false)")
    conn.commit()
    conn.close()
    print("Done. Your old SQLite data is now in PostgreSQL.")


if __name__ == "__main__":
    main()
