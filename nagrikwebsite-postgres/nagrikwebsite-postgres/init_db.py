"""Creates all NAGRIK AI tables in PostgreSQL.  Run once:  python init_db.py
Use the OWNER connection string in DATABASE_URL for this step."""
import database

if __name__ == "__main__":
    conn = database.get_db()
    cur = conn.cursor()
    cur.execute("SELECT current_database() AS db, current_user AS usr")
    info = cur.fetchone()
    conn.close()
    print(f"Connected to database '{info['db']}' as '{info['usr']}'")
    database.init_db()
    print("Tables ready:", ", ".join(database.REQUIRED_TABLES))
