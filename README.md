<div align="center">

<img src="static/assets/logo_full.png" alt="NAGRIK AI" width="360">

# NAGRIK AI — From Civic Problems to Actionable Solutions

**A civic issue reporting prototype built to help people describe local problems, share reports, and explore AI-assisted civic guidance.**

[Prototype status](#project-status) · [Setup guide](#run-nagrik-ai-locally) · [Neon database](#how-neon-postgresql-is-integrated) · [Screenshots](#project-showcase)

</div>

---

## Project showcase

The following visuals are taken from our project presentation. They explain the problem, prototype workflow, interface concept, value, and future direction.

<p align="center">
  <img src="docs/presentation-assets/image-1-1.jpg" alt="NAGRIK AI title slide" width="90%">
</p>

<p align="center"><em>Figure 1 — NAGRIK AI: From Civic Problems to Actionable Solutions.</em></p>

<details>
<summary><strong>More slides from our presentation</strong> (click to expand)</summary>

### The problem and our solution
![Problem statement and solution](docs/presentation-assets/image-2-1.jpg)

### Working of our current prototype
![Prototype workflow](docs/presentation-assets/image-3-1.jpg)

### Glimpses of our prototype
![Prototype overview](docs/presentation-assets/image-4-1.jpg)

### What does it solve?
![Civic value](docs/presentation-assets/image-5-1.jpg)

### Practical commercial value
![Practical commercial value](docs/presentation-assets/image-6-1.jpg)

### Future vision
![Future vision of NAGRIK AI](docs/presentation-assets/image-7-1.jpg)

</details>

> **Live application screenshots:** The slides above are presentation visuals, not a claim that every screen or feature shown is fully implemented. Add fresh screenshots from the running code in the spaces below.

### Screenshots from the running application

| Screen | Add your screenshot |
|---|---|
| Login / sign-in page | `docs/screenshots/01-login.png` |
| Main civic feed | `docs/screenshots/02-home-feed.png` |
| Create a report | `docs/screenshots/03-create-report.png` |
| Category statistics / map | `docs/screenshots/04-statistics-map.png` |
| AI civic guidance / chat | `docs/screenshots/05-ai-guidance.png` |
| UPKAR-ML message checker | `docs/screenshots/06-ml-checker.png` |
| UPKAR-LLM assistant | `docs/screenshots/07-llm-assistant.png` |

Create a `docs/screenshots/` folder and place screenshots with the exact filenames above, or update the paths. The screenshots are intentionally left as placeholders; they will not display until you add the files.

---

## Project status

**NAGRIK AI has not been deployed or hosted publicly.** We have not published a live website because of financial constraints and the complexity of bringing the different components and technologies together into a reliable hosted service.

The project **runs on our development system**. We are sharing the source so others can set it up locally. Since machines and environments differ, we cannot guarantee that it will run without configuration changes on every computer. Follow the setup instructions below and configure your own Neon database and API key where required.

Some interface areas are incomplete. In particular, **notifications and the Problem tabs/sections are not fully working yet**. We are actively working on these features and plan to improve their integration and reliability.

### What is included

- **Main web application:** Flask backend with HTML, CSS and JavaScript frontend.
- **Civic posts:** login, create/view posts, category filtering, likes, comments, and statistics/map endpoints implemented in the main app.
- **Neon PostgreSQL:** hosted PostgreSQL database connection configured through `DATABASE_URL`.
- **Text moderation:** rule-based checks in the main app (`ml_filter.py`).
- **UPKAR-ML:** separate Flask app using a trained `LinearSVC` model and `CountVectorizer` to classify Hindi/English messages.
- **UPKAR-LLM:** separate Streamlit assistant that structures complaint descriptions and can provide AI-assisted guidance through Groq when configured.
- **AI civic guidance:** `civic_llm.py` calls Groq when an API key is available and has a local rule-based fallback.

> The main Flask site, UPKAR-ML, and UPKAR-LLM are **separate run processes**. They are not launched together by a single command, and their data stores/features are not all synchronized.

## Technology stack

| Component | Technologies |
|---|---|
| Main application | Python, Flask, Jinja templates, HTML, CSS, JavaScript |
| Database | PostgreSQL on Neon; `psycopg2` connection pool |
| Environment configuration | `python-dotenv` |
| Civic guidance | Groq API (optional; local fallback exists in the main app) |
| Main-app text checks | Python rules in `ml_filter.py` |
| Standalone moderation | Flask, scikit-learn, `CountVectorizer`, `LinearSVC`, NLTK / Indic NLP dependencies |
| Standalone assistant | Streamlit, LangChain, LangGraph, Groq, Pillow, pandas, NumPy |

---

## Repository structure

```text
nagrikwebsite-postgres/
├── app.py                         # Main Flask routes and API
├── run.py                         # Starts the main Flask application
├── database.py                    # PostgreSQL connection + schema helpers
├── init_db.py                     # Initializes required PostgreSQL tables
├── migrate_sqlite_to_postgres.py   # Optional SQLite-to-PostgreSQL migration
├── seed_data.py                    # Optional sample-data generator
├── setup_roles.sql                 # Optional restricted database role example
├── ml_filter.py                    # Main app's text moderation
├── civic_llm.py                    # AI civic guidance and fallback logic
├── requirements.txt
├── .env.example                    # Safe environment-variable template
├── templates/
│   ├── index.html
│   └── login.html
├── static/
│   ├── css/
│   ├── js/
│   ├── assets/
│   └── uploads/
├── UPKAR-ML/
│   ├── app.py                      # Standalone moderation web app/API
│   ├── preprocess.py
│   ├── Model/                      # model.pkl and vectorizer.pkl
│   ├── dataset/
│   └── notebooks/training.ipynb
├── UPKAR-LLM/
│   ├── app.py                      # Standalone Streamlit assistant
│   └── data/complaints.jsonl
└── docs/
    ├── presentation-assets/         # Images extracted from our PPT
    └── screenshots/                 # Add local application screenshots here
```

---

## Requirements

- Python 3.10+ recommended.
- `pip` and a terminal / command prompt.
- A [Neon](https://neon.tech/) account and PostgreSQL connection string for the main web app.
- A Groq API key for model-backed features. Some main-app guidance may fall back to local rules without it; the standalone UPKAR-LLM assistant requires a working key for its AI workflow.
- Internet access for installing Python packages and for external API calls.

**Important:** This version of the main application uses PostgreSQL, not the SQLite database setup described in some earlier project notes. The bundled `nagrik.db` file is from an earlier SQLite version and is not the active database used by this PostgreSQL configuration.

## Run NAGRIK AI locally

### 1. Download and extract the project

Extract the ZIP, open the `nagrikwebsite-postgres` folder in VS Code (or another editor), and open a terminal in that folder.

### 2. Create a virtual environment

**Windows PowerShell**
```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

**macOS / Linux**
```bash
python3 -m venv .venv
source .venv/bin/activate
```

If PowerShell blocks activation, either allow script activation for your user according to your organization's policy or run the commands from Command Prompt using `.venv\Scripts\activate.bat`.

### 3. Install the dependencies

From the project root:

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

The root requirements file includes dependencies for the main application and the AI/ML modules. If a package fails to install, check your Python version and the package's platform support.

### 4. Create a Neon database

1. Sign in to [Neon](https://neon.tech/) and create a project.
2. In the Neon dashboard, open **Connect** and select the database and role you intend to use.
3. Copy the PostgreSQL connection string. Use the pooled connection string if that is the option Neon recommends for your application, and ensure SSL is enabled (`sslmode=require`).
4. Keep the connection string private. It contains credentials.

The connection string usually follows this pattern (replace every placeholder with your actual values):

```text
postgresql://DB_USER:DB_PASSWORD@YOUR_NEON_HOST/DB_NAME?sslmode=require
```

Do not copy the example literally. Use the actual connection string shown by your Neon dashboard.

### 5. Configure `.env`

Copy the template:

**Windows PowerShell**
```powershell
Copy-Item .env.example .env
```

**macOS / Linux**
```bash
cp .env.example .env
```

Open `.env` and set the values:

```dotenv
DATABASE_URL=postgresql://DB_USER:DB_PASSWORD@YOUR_NEON_HOST/DB_NAME?sslmode=require
SECRET_KEY=replace-this-with-a-long-random-secret
GROQ_API_KEY=your_groq_api_key
```

- `DATABASE_URL` is required for the main Flask app.
- `SECRET_KEY` should be a long random value; do not use the fallback key for a public deployment.
- `GROQ_API_KEY` is optional for the main app's local fallback behavior but required for Groq-powered responses and the standalone assistant.

**Never commit `.env` or share your Neon password / API keys.** If a credential has been exposed, rotate it.

### 6. Initialize the Neon database tables

Run this once from the project root:

```bash
python init_db.py
```

The script connects using `DATABASE_URL` and creates the tables needed by the application if they do not already exist. The database role used for first-time setup must have permission to create tables and sequences.

If initialization fails, verify:
- `DATABASE_URL` is copied correctly from Neon.
- The database name and role are correct.
- The URL includes `sslmode=require`.
- Your network permits the connection.
- The role has schema/table creation permissions.

### 7. Start the main web app

```bash
python run.py
```

Open the local address printed by the app, normally:

**http://127.0.0.1:5000**

The application is now running on your own computer. This is a local development server, **not a public deployment**. Keep the terminal running while you use the website.

### 8. Sign in and test

Use the login page to sign in. In the current code, a username that does not exist can be registered by submitting a username, display name (if requested), and password through the login flow. Use test credentials only, and remember the credentials you create.

Try creating a sample civic report, browsing the feed, using available like/comment actions, and checking the statistics. Some interface items are still incomplete; see [Known limitations](#known-limitations).

---

## How Neon PostgreSQL is integrated

We use **Neon as the PostgreSQL database provider**. The application does not hard-code the real database password in Python; it reads the connection string from the `DATABASE_URL` environment variable.

The integration is implemented mainly in `database.py`:

1. `python-dotenv` loads environment variables from `.env`.
2. `DATABASE_URL` supplies the Neon PostgreSQL connection details, including the host, database, username, password, and SSL setting.
3. `psycopg2` connects to PostgreSQL. The code uses a small threaded connection pool to reuse connections instead of opening a new connection for every request.
4. `database.init_db()` creates the required tables when they are missing. The schema includes users, posts, likes, solution votes, comments, LLM messages, and complaints.
5. The main Flask routes call functions in `database.py` to read and write application data.

The setup flow is:

```text
Browser (HTML / CSS / JavaScript)
                |
                v
          Flask app.py
                |
                v
        database.py / psycopg2
                |
        DATABASE_URL in .env
                |
                v
       Neon PostgreSQL database
```

### Optional: migrate old SQLite records

The project includes `migrate_sqlite_to_postgres.py` to copy data from the older `nagrik.db` SQLite file into PostgreSQL. This is **optional**; a fresh setup does not need migration. Read the script before using it. It refuses to copy into a database that already contains users/posts unless `--force` is passed. **Using `--force` can truncate existing PostgreSQL tables and delete their data. Back up first.**

```bash
python migrate_sqlite_to_postgres.py
```

### Optional: restricted app database role

`setup_roles.sql` is an optional example for creating a limited role after the tables exist. Review and edit its role name/password before running it in the Neon SQL Editor. Do not use the sample password in a real environment. Use an owner/admin connection only for initialization or migrations; a restricted runtime role is safer when configured correctly.

---

## Run the separate AI/ML components

These components are optional and are **not started automatically** when you run `python run.py`.

### UPKAR-ML — Hindi/English message checker

Open a second terminal:

```bash
cd UPKAR-ML
python -m venv .venv
```

Activate the environment using the earlier instructions, then:

```bash
pip install -r requirements.txt
python app.py
```

Open **http://127.0.0.1:5000** unless the port is already in use. If the main application is using port 5000, start this app on a different port:

```bash
flask --app app run --port 5001
```

The app exposes:
- `GET /` — message-checker interface
- `POST /predict` — classifies a JSON `message`
- `GET /health` — simple health check

Example request body:
```json
{"message": "Please repair the pothole near the school."}
```

**Folder-name note:** The current code in `UPKAR-ML/app.py` looks for `UPKAR-ML/model/` (lowercase), while the provided archive contains `UPKAR-ML/Model/` (uppercase). On case-sensitive systems this can prevent model loading. Either rename `Model` to `model` or update `MODEL_DIR` in `UPKAR-ML/app.py` to match the folder name.

### UPKAR-LLM — AI complaint assistant

Open another terminal from the project root:

```bash
cd UPKAR-LLM
python -m venv .venv
```

Activate the environment, then install its dependencies:

```bash
pip install -r requirements.txt
```

Create `UPKAR-LLM/.env` and add your own key:

```dotenv
GROQ_API_KEY=your_groq_api_key
```

Start the assistant:

```bash
streamlit run app.py
```

Open the local URL printed by Streamlit, commonly **http://localhost:8501**.

The assistant is a separate Streamlit process and stores its records in `UPKAR-LLM/data/complaints.jsonl`. Its data is not automatically synchronized with the main Flask application's Neon database.

---

## Typical user flow

1. A citizen opens NAGRIK AI and signs in.
2. The citizen creates a report with a civic category, title/description, location, and optional image.
3. The main app applies its text-checking logic and stores accepted report data in PostgreSQL.
4. Reports can appear in the feed; supported actions include likes, comments, and solution feedback.
5. Category/statistics and map-related API endpoints provide data for the frontend.
6. When configured, Groq can generate AI-assisted civic guidance. The main app also includes rule-based fallback guidance.
7. The standalone UPKAR-ML checker and UPKAR-LLM assistant can be launched separately for their respective workflows.

AI suggestions are experimental and should not be treated as official government decisions. Confirm the responsible authority and any contact details using official sources.

## Known limitations and work in progress

We want to be transparent about what is and is not complete in this prototype.

- **Not deployed/hosted:** The project has no public production URL. Financial constraints and the effort involved in integrating multiple components/languages have delayed hosting. It currently runs on our development system.
- **Notifications:** Notifications are not fully working yet. We are working on this feature.
- **Problem tabs/sections:** These tabs/sections are not fully functional yet. We are working on their behavior and integration.
- **Separate processes:** The main Flask application, UPKAR-ML, and UPKAR-LLM must be launched separately.
- **Separate data stores:** UPKAR-LLM's JSONL complaint records do not automatically sync to Neon.
- **ML model path:** The `Model` versus `model` folder-name mismatch can affect UPKAR-ML on case-sensitive systems.
- **AI dependence:** Groq-powered responses need a valid API key, network access, and an available model. Provider model names/limits can change.
- **Prototype quality:** Moderation and generated civic guidance can make mistakes. Review results instead of relying on them as final decisions.
- **Security hardening:** Before public release, review authentication, session secrets, upload validation, rate limiting, privacy, error handling, and production server settings.

## Troubleshooting

| Problem | Things to check |
|---|---|
| `psycopg2` cannot connect | Check Neon host, password, database name, `DATABASE_URL`, network, and `sslmode=require`. |
| Missing database/table errors | Run `python init_db.py` using a role with table-creation privileges. |
| `GROQ_API_KEY` errors | Add a valid key to the correct `.env`; restart the process after editing it. |
| Port 5000 is already in use | Stop the other server or choose a different port. |
| UPKAR-ML says model file is missing | Check the `Model` / `model` capitalization and confirm both pickle files exist. |
| Streamlit command not found | Activate the environment and install `UPKAR-LLM/requirements.txt`. |
| A feature/tab does not respond | It may be one of the known incomplete features; check the browser console and terminal logs. |

## Security and responsible use

- Keep `.env`, database credentials, API keys, and real user information private.
- Use a unique `SECRET_KEY`.
- Do not use the Flask development server as a public production server.
- Validate uploaded file types and sizes before a public launch.
- Do not treat AI-generated advice as an official government response.
- Use demo data for screenshots and public demonstrations.

## Future improvements

- Complete notifications and Problem tabs/sections.
- Improve integration between the main application and standalone AI/ML components.
- Improve image validation and civic-issue classification.
- Improve moderation using representative, carefully evaluated Hindi/English data.
- Replace simple location rules with reliable geocoding and validated civic GIS data.
- Improve testing, security, deployment configuration, and monitoring.
- Evaluate and deploy a production-ready hosted version when resources allow.

## Contributing / feedback

Suggestions and bug reports are welcome. When reporting an issue, include:
- What you tried to do.
- Steps to reproduce the issue.
- Expected versus actual behavior.
- Relevant error messages, with passwords, API keys, and personal information removed.

## License

No license file was included with this project. Unless a license is added, do not assume the repository is licensed for unrestricted reuse.
