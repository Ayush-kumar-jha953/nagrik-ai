-- Run in the Neon SQL Editor (or psql) as the OWNER, AFTER `python init_db.py`.
-- Creates a limited login for friends. Change the password first.
-- Replace "nagrik" below if your database has another name.

CREATE ROLE friend_app LOGIN PASSWORD 'choose-a-strong-password';
GRANT CONNECT ON DATABASE nagrik TO friend_app;
GRANT USAGE ON SCHEMA public TO friend_app;

-- what the app needs: read, add, change rows
GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA public TO friend_app;
-- the app removes a row when someone un-likes / un-votes
GRANT DELETE ON post_likes, solution_votes TO friend_app;
-- auto-number counters (id columns)
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO friend_app;

-- not granted: CREATE / DROP / ALTER / TRUNCATE, and DELETE on posts, users, comments
