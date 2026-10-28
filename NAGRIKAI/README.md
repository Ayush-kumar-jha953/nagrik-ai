# NAGRIK AI - Civic Problem Platform & AI Assistant

A full-stack civic engagement and grievance reporting application built according to the uploaded UI designs and integrating **UPKAR-ML** for post moderation and **UPKAR-LLM** for the civic AI assistant.

---

## 🌟 Key Features & Architecture

### 1. Frontend (Pixel-Perfect to Provided Designs)
- **Image 1: Authentication / Profile Screen**
  - NAGRIK AI branding: *"DATA DRIVEN CIVIC SOLUTIONS | PRIORITIZING OUR PROBLEMS"*.
  - Clean profile inputs (`Name`, `Username`, `Password`) accessible via the top-right profile avatar.
- **Image 2: Main Civic Feed & Dashboard**
  - **Top Navigation Bar:** Official logo and user profile pill.
  - **Left Sidebar:** Navigation for `🏠 Home` (active state), `🎯 Problems`, `➕ Post`, `🔔 Notification`, and `⚙️ Settings`.
  - **Center Feed:** Civic problem cards with full-width images, thumb-up like pills (with like toggles), speech bubble comment counters, author usernames (`Navneeta123@a`, `meenu123@a`), and category badges (e.g. `Infrastructure`, `Sanitation`).
  - **Right Sidebar ("Issues by category"):** Real-time dynamic count bars matching the screenshot:
    - Climate Issue (0)
    - Healthcare (1)
    - Education (0)
    - Sanitation (1)
    - Infrastructure (2)
  - **Floating Bot Icon:** Bottom-right circular robot icon with pulsing status indicator that toggles the AI assistant.
- **Image 3: Create Post Modal Dialog**
  - Problem photo preview with file picker.
  - Category selector (`Infrastructure`, `Sanitation`, `Healthcare`, `Education`, `Climate Issue`).
  - Detailed problem description textarea with live validation.
  - **UPKAR-ML Moderation Integration:** If content is flagged, displays an alert:
    > *"Your post cannot be posted. It has been flagged by our civic content moderation system for review..."*
  - `Cancel` and `Upload` buttons.

---

### 2. Machine Learning Moderation (UPKAR-ML Integration)
- Integrated via [`ml_filter.py`](file:///c:/Users/Ayush%20Kumar%20Jha/OneDrive/Documents/Antigravity/ml_filter.py).
- Uses `preprocess.py` for English and Hindi text cleaning, stopword removal, and Porter stemming.
- Evaluates text using the trained `LinearSVC` model and `CountVectorizer` (`model.pkl` & `vectorizer.pkl`).
- Flagged posts are rejected before hitting the database, protecting civic discourse from abuse, profanity, or spam links.

---

### 3. Civic AI Assistant (UPKAR-LLM Integration)
- Integrated via [`civic_llm.py`](file:///c:/Users/Ayush%20Kumar%20Jha/OneDrive/Documents/Antigravity/civic_llm.py) into the bottom-right floating bot icon.
- Features:
  - **Authority Routing:** Directs issues to the right department (PWD, Municipal Corporation Sanitation Wing, Jal Board, DISCOM, CMO, SPCB).
  - **Official Channels & Escalation:** Informs citizens about official portals (Swachhata App, CM Helpline, CPGRAMS, RTI).
  - **Root Cause & Long-Term Solutions:** Suggests structural prevention measures and RWA citizen actions.
  - **Structured Complaint Filing:** Synthesizes complaints and assigns unique tracking IDs saved in SQLite.
  - **Area Reports:** Summarizes complaints and category breakdowns.
  - **Hybrid Engine:** Operates automatically in high-precision local rule mode, and seamlessly utilizes Groq (`ChatGroq`) when `GROQ_API_KEY` is provided.

---

### 4. Backend & Database (SQLite)
- Built with Python `Flask` and `sqlite3` ([`database.py`](file:///c:/Users/Ayush%20Kumar%20Jha/OneDrive/Documents/Antigravity/database.py)):
  - `users`: User profiles and authentication.
  - `posts`: Civic feed reports with like/comment counts and ML scores.
  - `post_likes`: Prevents duplicate likes per user.
  - `post_comments`: Community discussions on reports.
  - `complaints`: Structured grievances filed via the AI assistant.
  - `llm_messages`: Chat logs for assistant conversations.

---

## 🚀 Running the Application

To start the server:
```powershell
python run.py
```
Then open your web browser and navigate to:
```
http://127.0.0.1:5000
```

## 🧪 Running Automated Tests
```powershell
python test_app.py -v
```
All 8 test suites verify:
- HTML rendering and navigation elements
- Dynamic category counts and seed posts
- Post creation passing UPKAR-ML
- Inappropriate post rejection and polite moderation alerts
- Link spam rejection
- Like toggle and comment persistence in SQLite
- UPKAR-LLM queries (complaints, authority lookup, prevention plans, area reports)

