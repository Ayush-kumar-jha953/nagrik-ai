# Deploying NAGRIK AI

1. **Rotate your Groq key first.** The old key was hardcoded in `civic_llm.py` and `.env`
   (both removed here). Create a new one at console.groq.com and revoke the old one.
2. Push this folder to a GitHub repo (`.gitignore` already excludes `.env`).
3. On render.com: New > Blueprint > select the repo (uses `render.yaml`).
   Paste the new `GROQ_API_KEY` when prompted.
4. Open the URL Render gives you (`https://nagrik-ai-xxxx.onrender.com`).

Notes
- The persistent disk (needed so posts/images survive restarts) requires a paid Render plan.
  On the free plan, remove the `disk:` and `DATA_DIR` lines; the app works but new posts
  reset on each redeploy/restart.
- Local run: `pip install -r requirements.txt && python run.py`
- Without a Groq key the app still works using its built-in rule-based Delhi guidance.
