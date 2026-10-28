# NAGRIK AI (UPKAR)

**Data-driven civic solutions | Prioritizing our problems**

NAGRIK AI is a civic-problem platform for India. Citizens photograph a problem in their area (pothole, garbage dump, broken school building, and so on), describe it, and share it with the community, while AI components help check message quality and turn plain-language complaints into structured reports that name the right authority.

## What the flow does (in one line)

A citizen logs in, uploads a photo of a local civic problem with a category and description, and it appears in a community feed where others can upvote and comment, the owner is notified of comments, and a live chart shows issues by category; alongside this, an ML message checker and an LLM complaint assistant (each built as its own module) handle language moderation and complaint structuring.

## Project status at a glance

This submission contains **four working pieces in three folders**. Each part was built and tested on its own, and each runs independently. **They are not yet connected into one running application** (see [Integration status](#integration-status)).

| Part | Folder | Stack | What it does | Status |
|---|---|---|---|---|
| Backend + Frontend | `UPKAR-test2/` | Flask, PostgreSQL, Jinja2 / HTML / CSS / JavaScript | Login, photo posts, likes, comments, notifications, category chart | Working on its own |
| ML | `UPKAR-ML/` | scikit-learn (CountVectorizer + LinearSVC), Flask | Classifies a Hindi / English message as acceptable or flagged for review | Working on its own |
| LLM | `UPKAR-LLM/` | Streamlit, LangChain agent, Groq | Multilingual complaint assistant with tools for authorities, photos and reports | Working on its own (needs a free Groq API key) |

## Hosted link / demo

There is no hosted link or demo video yet. Instead, every part includes screenshots of it running, in its `workingimages/` folder. They are embedded below in each part's section.

## Repository layout

```
.
├── README.md
├── UPKAR-test2/              # Backend + frontend (Flask + PostgreSQL)
│   ├── app.py                # Routes: home, problems, notifications, upload, like, comment, stats
│   ├── auth.py               # Login / signup blueprint
│   ├── db.py                 # PostgreSQL connection helper (3 databases)
│   ├── init db.py            # One-time script that creates the 3 databases and tables
│   ├── templates/            # HTML pages (base.html holds the CSS and JS)
│   ├── static/               # Logos (uploaded photos are saved in static/uploads/)
│   └── workingimages/        # Screenshots of this part working
├── UPKAR-ML/                 # Message moderation model + small web app
│   ├── app.py                # Flask app: web page + /predict API
│   ├── preprocess.py         # Text cleaning (must match the notebook)
│   ├── model/                # model.pkl and vectorizer.pkl (trained model)
│   ├── notebooks/training.ipynb
│   ├── dataset/              # 3,098 labelled Hindi / English civic messages (CSV)
│   ├── templates/, static/   # Web page for the checker
│   ├── requirements.txt, Procfile
│   └── workingimages/
└── UPKAR-LLM/                # LLM complaint assistant
    ├── app.py                # Streamlit app + LangChain agent + tools
    ├── requirements.txt
    ├── data/complaints.jsonl # Saved complaints (contains one sample record)
    └── workingimages/
```

No `node_modules`, virtual environments, build folders or `.env` files are included. The frontend is plain server-rendered HTML, so **no Node.js or npm is needed**. No API keys or passwords are stored in the code; you supply your own through environment variables (see each part's setup).

## Prerequisites

- Python 3.10 or newer (3.12 was used to verify the ML app)
- PostgreSQL 13 or newer, running locally (backend only)
- A free Groq API key from <https://console.groq.com> (LLM part only)
- Internet access on first run (ML part downloads NLTK stopwords; LLM part calls Groq)

Each part has its own dependencies, so use a **separate virtual environment per part**:

```bash
python -m venv venv
# Windows:      venv\Scripts\activate
# macOS/Linux:  source venv/bin/activate
```

> **Port note:** the backend and the ML app are both Flask apps that default to port 5000. If you run both at once, start the ML app on another port (shown in Part 2).

---

## Part 1: Backend + Frontend (`UPKAR-test2/`)

A Flask application with a social-feed style interface for reporting civic problems. Data lives in PostgreSQL across four databases:

| Database | Table | Holds |
|---|---|---|
| `nagrik_db` | `users` | Accounts (passwords are stored as salted hashes) |
| `image` | `picture_uploaded` | Posts: user, category, description, photo filename |
| `upvote` | `count` | Like count per post |
| `comment` | `num` | Comments, with post owner and commenter |

### Setup

1. **Install dependencies** (there is no requirements file for this part):

   ```bash
   cd UPKAR-test2
   pip install flask psycopg2-binary python-dotenv
   ```

2. **Create a `.env` file** inside `UPKAR-test2/` (this file is never committed):

   ```
   PGHOST=localhost
   PGPORT=5432
   PGUSER=postgres
   PGPASSWORD=your_postgres_password
   LOGIN_DB_NAME=nagrik_db
   SECRET_KEY=any-long-random-string
   ```

3. **Also set the same database variables in your terminal** before running. `auth.py` reads `.env`, but `db.py` reads its settings before `.env` is loaded, so without this step the data features would try the placeholder password.

   ```bash
   # macOS / Linux
   export PGHOST=localhost PGPORT=5432 PGUSER=postgres PGPASSWORD=your_postgres_password
   ```
   ```powershell
   # Windows PowerShell
   $env:PGHOST="localhost"; $env:PGPORT="5432"; $env:PGUSER="postgres"; $env:PGPASSWORD="your_postgres_password"
   ```

   (Alternatively, add `load_dotenv()` right after the imports in `db.py` and skip this step.)

4. **Create the login database** (the init script creates the other three, but not this one):

   ```bash
   psql -U postgres -c "CREATE DATABASE nagrik_db;"
   ```

5. **Create the remaining databases and tables** (run once). The file name contains a space, so keep the quotes:

   ```bash
   python "init db.py"
   ```

   Expected output: `created database image`, `created database upvote`, `created database comment`, then `table ready in ...` for each.

6. **Start the app** (use `python app.py`, which also creates the `users` table on start):

   ```bash
   python app.py
   ```

   Open <http://127.0.0.1:5000>.

### How to use it

1. **Log in or sign up on the first page.** Enter a name, a username and a password. A new username is registered automatically; an existing username is checked against its password. You land on the Home feed.
2. **Report a problem.** Click **+ Post** in the sidebar, choose a JPG or PNG (max 5 MB), pick a category (Climate Issue, Healthcare, Education, Sanitation or Infrastructure), write a description of at least 10 characters, and click **Upload**.
3. **Browse the feed.** Home shows every citizen's posts, newest first.
4. **Upvote and comment.** Click the thumbs-up to like (click again to undo). Click the speech bubble to open the comments and add one.
5. **Check your own posts.** **Problems** lists only what you have uploaded.
6. **See who responded.** **Notification** lists comments other citizens left on your posts.
7. **Read the chart.** The right-hand panel shows the number of issues per category and updates as posts are added.
8. **Log out** by opening <http://127.0.0.1:5000/logout>.

### Screenshots

<table>
  <tr>
    <td width="50%" valign="top"><img src="https://github.com/user-attachments/assets/57d60a8f-0d3b-41d7-9c8c-2e137e921b58" alt="Login page" width="100%"><br><sub>1. Login / signup</sub></td>
    <td width="60%" valign="top"><img src="https://github.com/user-attachments/assets/4f998241-5804-4980-9d45-6c1e10527562" alt="Home feed with category chart" width="100%"><br><sub>2. Home feed with the issues-by-category chart</sub></td>
  </tr>
  <tr>
    <td width="50%" valign="top"><img src="https://github.com/user-attachments/assets/2c28c1da-731d-4653-8f57-18c88e932812" alt="Post feed" width="100%"><br><sub>3. Posts with descriptions, likes and categories</sub></td>
    <td width="50%" valign="top"><img src="https://github.com/user-attachments/assets/3ed71448-6a87-49d6-bf88-62f4ec7646bb" alt="Report a problem" width="100%"><br><sub>4. Report-a-problem form (photo, category, description)</sub></td>
  </tr>
  <tr>
    <td width="50%" valign="top"><img src="https://github.com/user-attachments/assets/04f6101f-e80f-4e89-a5d9-27013e2c624d" alt="Notifications" width="100%"><br><sub>5. Notifications for comments on your posts</sub></td>
    <td width="50%" valign="top"><img src="https://github.com/user-attachments/assets/a7e4ec9d-d5fd-490b-ba67-1d119b15719f" alt="Users table in PostgreSQL" width="100%"><br><sub>6. <code>users</code> table in PostgreSQL (passwords stored hashed)</sub></td>
  </tr>
  <tr>
    <td width="50%" valign="top"><img src="https://github.com/user-attachments/assets/d8e3c660-8307-4e7f-a00d-d092d2f0e5d6" alt="Posts table in PostgreSQL" width="100%"><br><sub>7. <code>picture_uploaded</code> table in PostgreSQL</sub></td>
    <td width="50%"></td>
  </tr>
</table>

### Not functional / limitations in this part

- **Profile and Settings pages are placeholders.** Profile shows "Welcome" and Settings says it is coming soon.
- **The chatbot button (bottom-right) is a placeholder.** It shows a "coming soon" message and is not connected to the LLM part.
- **Like tracking is per session.** The like count is stored in the database, but which posts you have already liked is kept in your browser session, so logging out and back in lets you like a post again.
- **No logout button** in the interface; use the `/logout` address.
- **Development setup only:** the app runs in Flask debug mode, and uploaded photos are saved on local disk in `static/uploads/`.
- The ML moderation (Part 2) is **not** applied to posts or comments yet.

---

## Part 2: ML message checker (`UPKAR-ML/`)

A text classifier that decides whether a Hindi or English civic message is suitable for public discussion ("good") or should be flagged for review ("bad", for example abusive or personally insulting text). It ships with the trained model, the training notebook, the dataset, and a small web page and API to try it.

**How it works:** the message is cleaned (letters only, Hindi and English stopwords removed, English words stemmed), converted to word and word-pair counts (CountVectorizer, up to 5,000 features), and scored by a LinearSVC model (C = 0.01). The dataset holds 3,098 labelled messages (about half Hindi, half English, including mixed-script text), with 1,508 good and 1,590 bad.

### Setup

```bash
cd UPKAR-ML
python -m venv venv && source venv/bin/activate     # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

Notes on setup:

- **Model folder name:** `app.py` loads the model from a folder called `model/` (lowercase) containing `model.pkl` and `vectorizer.pkl`. If your copy has `Model/` with a capital M, rename it to `model/`. Windows is forgiving about this, but Linux and some macOS setups are not.
- `requirements.txt` also lists notebook-only libraries (pandas, matplotlib, seaborn, indic-nlp-library). The web app itself needs only `flask`, `scikit-learn` and `nltk`.
- The first run downloads the NLTK English stopword list, so you need an internet connection once.

### Run

```bash
python app.py                          # http://127.0.0.1:5000
# if the backend is already using port 5000:
flask --app app run --port 5001        # http://127.0.0.1:5001
```

(`Procfile` contains a `gunicorn` start command for deployment on Linux hosts. It is included for future hosting but has not been deployed, and `gunicorn` is not in `requirements.txt`.)

### How to use it

**In the browser:** type or paste a Hindi or English message (up to 2,000 characters) and click **Check message**. You get either **Acceptable** (green) or **Flagged for review** (red), with a meter showing the model's signal strength. The two example buttons fill in sample English and Hindi text. If a message has too few meaningful words, you get "Not enough text to judge".

**As an API:**

```bash
curl -X POST http://127.0.0.1:5000/predict \
     -H "Content-Type: application/json" \
     -d '{"message": "Please repair the sewage overflow near the public park"}'
# {"confidence": 0.644, "label": "good", "score": -0.593}

curl http://127.0.0.1:5000/health      # {"status": "ok"}
```

`label` is `good`, `bad` or `unclear`. `confidence` is a rough signal strength between 0.5 and 1, **not** a calibrated probability.

**Retraining:** open `notebooks/training.ipynb` in Jupyter (extra packages: `jupyter`, `pandas`, `matplotlib`, `seaborn`). The notebook reads the CSV by bare file name, so copy `dataset/indian_civic_language_moderation_hindi_english.csv` next to the notebook (or edit the path) before running. It saves `model.pkl` and `vectorizer.pkl`; move both into `model/`. Keep the cleaning code in `preprocess.py` identical to the notebook's.

### Screenshots

<table>
  <tr>
    <td width="50%" valign="top"><img src="https://github.com/user-attachments/assets/c34360e3-205a-446e-8645-30505286f4dd" alt="Acceptable result for a polite English message" width="100%"><br><sub>1. Polite English message: Acceptable</sub></td>
    <td width="50%" valign="top"><img src="https://github.com/user-attachments/assets/8e024f31-308f-472d-a772-00f00ff7260d" alt="Flagged result for an abusive Hindi-English message" width="100%"><br><sub>2. Abusive Hindi-English message: Flagged for review</sub></td>
  </tr>
  <tr>
    <td width="50%" valign="top"><img src="https://github.com/user-attachments/assets/22bafd1d-ab9f-48e4-a3d1-f286b0aae3d0" alt="Acceptable result for a civic repair request" width="100%"><br><sub>3. Civic repair request: Acceptable</sub></td>
    <td width="50%" valign="top"><img src="https://github.com/user-attachments/assets/841ea160-3771-43d1-8417-372a6c6e6d83" alt="Message checker home screen with example buttons" width="100%"><br><sub> />
 4. Message checker home screen with English and Hindi example buttons</sub></td>
  </tr>
</table>

### Not functional / limitations in this part

- **The reported 100% accuracy should not be read as real-world accuracy.** The notebook scores 1.00 on its held-out test split (620 messages), but the dataset is highly templated (many messages are variations of the same sentence patterns), so the test set is very similar to the training data. The shipped model was then trained on the full dataset, so it has no separate held-out score.
- **Messages outside the dataset's style can be misjudged.** For example, in a test run the app's own English example sentence ("The new road project will really help our village.") scored just above the "flagged" threshold, and borderline cases show low signal (around 55%). Treat the result as a helper for a human decision, as the interface says.
- Binary label only (good / bad); it does not say *why* a message was flagged. Hinglish written in Roman script is not specially handled.
- Not yet connected to the posting or commenting flow in Part 1.

---

## Part 3: LLM complaint assistant (`UPKAR-LLM/`)

A Streamlit chat app powered by a LangChain agent running on Groq. A citizen describes a problem in English, Hindi or Hinglish (optionally with photos), and the assistant:

1. Checks the text (currently blocks links), then converts it into a **structured complaint** (category, issue type, problem, duration, location, severity) saved to a local file.
2. Tells them **which authority to approach, where to report it, and how to escalate**, using a built-in table of Indian authorities and portals (the model is told not to invent offices or phone numbers).
3. Suggests **root causes and long-term prevention** for recurring problems.
4. Works with **photos** through tools: quality check (blur, brightness, resolution), GPS from photo metadata, a vision-model description, and simple enhancement (contrast, sharpen, brighten, resize, rotate).
5. Writes a short **area-level report** from the saved complaints.

### Setup

```bash
cd UPKAR-LLM
python -m venv venv && source venv/bin/activate     # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

Create a `.env` file inside `UPKAR-LLM/` (already listed in `.gitignore`):

```
GROQ_API_KEY=your_groq_api_key_here
# Optional: override the default models (Groq model names change over time)
# TEXT_MODEL=openai/gpt-oss-20b
# VISION_MODEL=meta-llama/llama-4-scout-17b-16e-instruct
```

### Run

```bash
streamlit run app.py        # opens http://localhost:8501
```

If the key is missing, the app shows an error asking you to add it to `.env`.

### How to use it

1. **Type a problem in any language** in the chat box, for example *"Hamare area mein pichle 5 din se kachra nahi uthaya gaya hai."*, or click one of the four **Try an example** buttons in the sidebar.
2. **Add photos (optional).** Use **Upload photos** in the sidebar (JPG, PNG or WEBP, up to 8). Then mention the photo in your message, for example *"Check my uploaded pothole image near my house and suggest what to do."* Use **Clear photos** to remove them.
3. **Read the answer.** For a complaint you get the saved complaint with its ID, the authority and how to report it, the escalation path, and a prevention plan. If you only ask a question ("Who should I report a pothole to?"), it answers without saving anything.
4. **Review saved complaints.** Open the **Saved complaints** panel at the top to see the table and download it as **CSV** or **JSON**. Complaints are stored in `data/complaints.jsonl` (the file included holds one sample record; delete it for a clean start).
5. **Get a summary.** Ask *"Write a short report of all complaints this month."*

### Screenshots

<table>
  <tr>
    <td width="50%" valign="top">
      <img
         src="https://github.com/user-attachments/assets/a4ec2460-6baf-426f-bcb2-e5fd8f386790"
          alt="Assistant home screen and greeting" width="100%"> 
      <br><sub>1. Home screen, example prompts and a Hindi greeting</sub>
    </td>
    <td width="50%" valign="top">
      <img
        src="https://github.com/user-attachments/assets/22204fbb-5e47-4b85-8dac-b1a069d77a13"
          alt="Who to report a pothole to" width="100%">
<br><sub>2. Authority and escalation answer for a pothole</sub>
    </td>
  </tr>
  <tr>
    <td width="50%" valign="top">
      <img
        src="https://github.com/user-attachments/assets/ea26875f-2179-4f04-81fb-f237b13037e3"
          alt="Complaint saved with an uploaded photo" width="100%">
<br><sub>3. Complaint saved with an uploaded photo (structured table)</sub>
    </td>
    <td width="50%" valign="top">
      <img
         src="https://github.com/user-attachments/assets/ef2ee698-706e-4c29-8a01-f21165410791" 
          alt="How to report the pothole" width="100%">
<br><sub>4. Where to report, and what to do next</sub>
    </td>
  </tr>
  <tr>
    <td width="50%" valign="top">
      <img
         src="https://github.com/user-attachments/assets/aee7a295-c684-4cb4-af17-b6f132b8e9e9" 
          alt="Long-term prevention plan" width="100%">
<br><sub>5. Long-term prevention plan and citizen actions</sub>
    </td>
    <td width="50%"></td>
  </tr>
</table>

### Not functional / limitations in this part

- **The local photo classifier and object detector are switched off in this submission.** The app can use optional local models (`ml/classifier.py`, `ml/detector.py`, `ml/text_filter.py`, `ml/analytics.py`) if they exist, but they are not part of this code, so the sidebar shows *Classifier: off | Detector: off* (visible in the screenshots). Photo questions fall back to the Groq vision model, and the text check only blocks links (there is no abuse filter here; the Part 2 model could fill that role later).
- **Answers come from a hosted language model**, so wording can vary between runs and contact details can be phrased loosely. The authority table is general for India, not city-specific, and every answer reminds the citizen to verify the local office or helpline.
- Some tables in the chat show a stray `<br>` where the model formatted line breaks.
- Complaints are saved to a local JSON-lines file, **not** to the PostgreSQL database from Part 1. Chat memory and uploaded photos live in memory and reset when the app restarts.
- Needs internet and a Groq key, and is subject to Groq's free-tier rate limits.
- Comments at the top of `app.py` mention an older file name (`nagric_agent.py`) and `requirements-agent.txt`; the correct commands are the ones in this README.

---

## Integration status

The backend and frontend, the ML message checker and the LLM assistant are **three separate programs**. They do not call one another, and there is no single command that starts everything. The plan for joining them is:

- Run the ML checker on post descriptions and comments before they are saved in Part 1.
- Connect the chatbot button in Part 1 to the LLM assistant.
- Store assistant complaints in the Part 1 database instead of a local file.

## Security notes

- No API keys, passwords or `.env` files are included. Create your own `.env` files as described above.
- Passwords in the `users` table are stored as salted hashes, never as plain text.
- Before any real deployment: set a strong `SECRET_KEY`, turn off Flask debug mode, and move uploaded photos to proper storage.
