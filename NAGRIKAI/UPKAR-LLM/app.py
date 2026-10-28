"""NAGRIK AI - civic problem assistant (Streamlit + LangChain agent on Groq).

What it does
  1. Turns a citizen's message (English / Hindi / Hinglish ...) into a structured complaint.
  2. Tells the citizen which authority to approach and how, and suggests long-term fixes.
  3. Works with uploaded photos through tools: quality check, GPS from the photo, category
     check, object detection, vision description and simple enhancement.
  4. Writes a short area-level report from all saved complaints.

Run:   streamlit run nagric_agent.py
Needs: GROQ_API_KEY in a .env file (see requirements-agent.txt).

The local ONNX models from the Flask project (ml/classifier.py, ml/detector.py,
ml/text_filter.py) are used when they exist. Without them the app still runs and falls back
to the vision LLM and a basic text check.
"""
import base64
import io
import json
import os
import re
import uuid
from datetime import datetime, timedelta, timezone
from typing import Literal

from dotenv import load_dotenv

load_dotenv()

import numpy as np
import pandas as pd
import streamlit as st
from langchain.agents import create_agent
from langchain.tools import tool
from langchain_core.messages import HumanMessage
from langchain_core.runnables import RunnableConfig
from langchain_groq import ChatGroq
from langgraph.checkpoint.memory import InMemorySaver
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageOps

# ---- optional local models from the Flask project ---------------------------------------
try:
    from ml.classifier import ImageClassifier
    CLASSIFIER = ImageClassifier()
except Exception:
    CLASSIFIER = None
try:
    from ml.detector import ObjectDetector
    DETECTOR = ObjectDetector()
except Exception:
    DETECTOR = None
try:
    from ml.text_filter import check_text as _local_check_text
except Exception:
    _local_check_text = None
try:
    from ml.analytics import DEPT_BY_LABEL
except Exception:
    DEPT_BY_LABEL = {"pothole": "Public Works Department (PWD)",
                     "garbage": "Municipal Corporation (Sanitation)",
                     "waterlogging": "Municipal Corporation (Drainage)"}

# ---- settings -----------------------------------------------------------------------------
TEXT_MODEL = os.getenv("TEXT_MODEL", "openai/gpt-oss-20b")
# Any Groq model that accepts images. Check Groq's model list - names change over time.
VISION_MODEL = os.getenv("VISION_MODEL", "meta-llama/llama-4-scout-17b-16e-instruct")
DATA_DIR = "data"
COMPLAINTS_FILE = os.path.join(DATA_DIR, "complaints.jsonl")
CATEGORIES = ["Climate", "Healthcare", "Education", "Sanitation", "Infrastructure"]
MAX_IMAGES = 8
CLASSIFIER_MIN_CONF = 0.60
NO_IMAGE = "No image uploaded yet. Ask the user to upload a photo in the sidebar."


# ---- per-session store (the example used one global dict; this keeps users apart) ---------
@st.cache_resource
def get_sessions() -> dict:
    return {}


SESSIONS = get_sessions()


def _new_session() -> dict:
    return {"images": {}, "pending": [], "seen": set()}


def _session(config) -> dict:
    tid = ((config or {}).get("configurable") or {}).get("thread_id", "default")
    return SESSIONS.setdefault(tid, _new_session())


def _clip(text: str, limit: int = 4000) -> str:
    return text if len(text) <= limit else text[:limit] + "\n... (truncated)"


# ---- image helpers --------------------------------------------------------------------------
def _gps_from_exif(img):
    """Return (lat, lng) from a photo's EXIF data, or None."""
    try:
        gps = img.getexif().get_ifd(0x8825)
        if not gps or 2 not in gps or 4 not in gps:
            return None

        def conv(v, ref):
            d, m, s = [float(x) for x in v]
            val = d + m / 60 + s / 3600
            return -val if ref in ("S", "W") else val

        return round(conv(gps[2], gps.get(1, "N")), 6), round(conv(gps[4], gps.get(3, "E")), 6)
    except Exception:
        return None


def _find_image(sess, name: str):
    """Return (key, entry) for an image name, or (None, error message)."""
    images = sess["images"]
    if not images:
        return None, NO_IMAGE
    name = (name or "").strip()
    if not name and len(images) == 1:
        key = next(iter(images))
        return key, images[key]
    if name in images:
        return name, images[name]
    for key in images:
        if key.lower() == name.lower():
            return key, images[key]
    return None, f"Image '{name}' not found. Available: {list(images)}"


def _queue_image(sess, img, caption: str):
    """Queue an image so the Streamlit UI shows it under the assistant's answer."""
    buf = io.BytesIO()
    img.convert("RGB").save(buf, "JPEG", quality=88)
    sess["pending"].append({"caption": caption, "bytes": buf.getvalue()})


def _to_data_url(img, max_side=1024) -> str:
    im = img.convert("RGB")
    im.thumbnail((max_side, max_side))
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=85)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()


def _severity_from(dets) -> float:
    if not dets:
        return 0.3
    top = max(d["confidence"] * d["area_ratio"] for d in dets)
    return round(min(1.0, 0.3 + 2.0 * top + 0.1 * (len(dets) - 1)), 3)


# ---- text safety -------------------------------------------------------------------------------
def _text_ok(text: str):
    if re.search(r"(https?://|www\.)\S+", text, re.I):
        return False, "Links are not allowed in complaints."
    if _local_check_text is not None:
        return _local_check_text(text)
    return True, ""


# ---- knowledge tables (the LLM explains these; it does not invent authorities) --------------
_MUNI_APP = "Your city's municipal helpline / grievance app (see the municipal corporation website)"
_STATE = "State government grievance portal or CM helpline"
_CPGRAMS = "CPGRAMS, the central grievance portal (pgportal.gov.in), for central government departments"

AUTHORITY_RULES = [
    (("Sanitation", None), ("garbage", "kachra", "waste", "trash", "dustbin", "litter", "sweep", "toilet"), {
        "authority": "Municipal Corporation / Municipal Council: Solid Waste Management and Sanitation wing",
        "channels": [_MUNI_APP, "Swachhata app (Swachh Bharat Mission - Urban)", "Ward sanitary inspector or ward office"],
        "escalate": "Municipal Commissioner's office, then the state urban development department"}),
    (("Infrastructure", "Sanitation", "Climate"), ("drain", "sewer", "sewage", "nala", "nallah", "waterlog", "flood", "naali"), {
        "authority": "Municipal Corporation: Drainage / Storm Water and Sewerage department",
        "channels": [_MUNI_APP, "Ward office", "District Disaster Management Authority if there is flooding"],
        "escalate": "Municipal Commissioner and the district collector's office"}),
    (("Infrastructure", None), ("pothole", "road", "footpath", "bridge", "speed breaker", "sadak", "gaddha"), {
        "authority": "Public Works Department (PWD) for state/national highways and major roads; the Municipal Corporation for city and colony roads",
        "channels": [_MUNI_APP, "PWD divisional office or its online complaint page", _STATE],
        "escalate": "Executive Engineer, then the Chief Engineer of the department"}),
    (("Infrastructure", None), ("streetlight", "street light", "light pole", "lamp", "batti"), {
        "authority": "Municipal electrical wing, or the electricity distribution company (DISCOM) where it maintains street lights",
        "channels": [_MUNI_APP, "DISCOM complaint line or app of your area"],
        "escalate": "Municipal Commissioner, or the DISCOM's circle office"}),
    (("Infrastructure", None), ("water supply", "pipeline", "leak", "tap", "drinking water", "pani"), {
        "authority": "Water supply department / Jal Board / Public Health Engineering department of your city or state",
        "channels": [_MUNI_APP, "Water board helpline or office of your area", _STATE],
        "escalate": "Executive Engineer, then the department head"}),
    (("Healthcare", None), ("hospital", "clinic", "doctor", "medicine", "dengue", "mosquito", "ambulance", "phc", "health"), {
        "authority": "District Chief Medical Officer (CMO) / State Health Department; the Municipal Health Officer for disease control in cities",
        "channels": ["Health department grievance line or portal of your state", _STATE,
                     "112 for emergencies, 108 for an ambulance in most states"],
        "escalate": "District Collector, then the state health department"}),
    (("Education", None), ("school", "teacher", "classroom", "midday", "mid-day", "student", "padhai"), {
        "authority": "Block Education Officer / District Education Officer; the state education department",
        "channels": ["School Management Committee (SMC) and the headmaster", "State education department grievance portal", _STATE],
        "escalate": "District Education Officer, then the state education department"}),
    (("Climate", None), ("pollution", "smoke", "burning", "air quality", "tree", "heat", "storm", "cyclone"), {
        "authority": "State Pollution Control Board for pollution; Forest / Horticulture department for trees; District Disaster Management Authority for storms and heat",
        "channels": ["State Pollution Control Board complaint page", _MUNI_APP, _STATE],
        "escalate": "District Collector, or the pollution board's regional office"}),
]
CATEGORY_DEFAULT = {
    "Sanitation": AUTHORITY_RULES[0][2], "Infrastructure": AUTHORITY_RULES[2][2],
    "Healthcare": AUTHORITY_RULES[5][2], "Education": AUTHORITY_RULES[6][2], "Climate": AUTHORITY_RULES[7][2],
}
GENERAL_NOTE = ("If the local office does not respond, escalate through the central grievance portal CPGRAMS "
                "(pgportal.gov.in, for central departments) or your state grievance portal / CM helpline, and use an "
                "RTI application to track what happened. Verify the exact office and helpline for your city, "
                "because they differ by state and city.")


def _lookup_authority(category: str, issue_type: str):
    text = (issue_type or "").lower()
    for cats, keywords, info in AUTHORITY_RULES:
        if category in cats and any(k in text for k in keywords):
            return info
    return CATEGORY_DEFAULT.get(category, CATEGORY_DEFAULT["Infrastructure"])


SOLUTION_RULES = [
    (("garbage", "kachra", "waste", "trash", "dustbin", "litter"), {
        "causes": ["Irregular collection routes or vehicle breakdowns", "No segregation at source", "Too few bins or secondary collection points"],
        "prevention": ["Door-to-door collection with GPS-tracked vehicles and a published schedule",
                       "Source segregation drive plus neighbourhood composting for wet waste",
                       "Ward-level monitoring: complaint count per ward reviewed monthly",
                       "Fines for dumping in open areas, with cameras at repeat dumping spots"],
        "citizen": ["RWA or ward committee audits the collection schedule", "Households segregate wet and dry waste"]}),
    (("pothole", "road", "footpath", "sadak", "gaddha"), {
        "causes": ["Poor drainage beside the road", "Weak construction quality", "Repairs after the monsoon done too late"],
        "prevention": ["Quality audits and a defect-liability period for road contractors",
                       "Fix drains and utility cuts before resurfacing",
                       "A pre-monsoon road survey and a time-bound repair target",
                       "Publish repair status per road so progress is visible"],
        "citizen": ["Report with photo and location early", "Track repeat spots to show the pattern to the department"]}),
    (("drain", "sewer", "sewage", "nala", "waterlog", "flood", "naali"), {
        "causes": ["Drains choked with waste and silt", "Encroachment on natural drains", "Too much paved surface and no rainwater absorption"],
        "prevention": ["De-silt drains before every monsoon with before/after photos",
                       "Remove encroachment on drains and restore natural water paths",
                       "Rainwater harvesting and permeable surfaces; retention ponds in low areas",
                       "Map flood-prone spots from complaints and fix the worst first"],
        "citizen": ["Do not dump waste in drains", "Join ward-level pre-monsoon inspections"]}),
    (("streetlight", "street light", "light pole", "lamp", "batti"), {
        "causes": ["No regular maintenance cycle", "Faults found only when citizens complain"],
        "prevention": ["Pole-wise asset register with a monthly check", "Smart or LED lights with fault alerts",
                       "Fixed repair time (for example 72 hours) with a public tracker"],
        "citizen": ["Report the pole number with the photo"]}),
    (("water supply", "pipeline", "leak", "tap", "pani"), {
        "causes": ["Old pipes and leakage", "Low pressure or irregular schedule"],
        "prevention": ["Replace old pipelines in priority areas", "Leak detection and metering", "Published supply timings and water-quality tests"],
        "citizen": ["Report leaks quickly", "Use water storage and harvesting where possible"]}),
    (("hospital", "clinic", "doctor", "medicine", "dengue", "mosquito", "phc", "health"), {
        "causes": ["Staff or medicine shortages", "Stagnant water and weak vector control"],
        "prevention": ["Regular vector-control drives and fogging only where surveys show need",
                       "Monthly stock and staffing checks at clinics with public display",
                       "Health camps and awareness in high-complaint areas"],
        "citizen": ["Remove standing water around homes", "Report clusters of fever cases to the local health office"]}),
    (("school", "teacher", "classroom", "midday", "mid-day", "student"), {
        "causes": ["Delayed repairs and no maintenance fund", "Vacancies and weak monitoring"],
        "prevention": ["A school maintenance fund and yearly safety audit", "Active School Management Committee that reports to the block office",
                       "Public dashboard of repairs and teacher vacancies"],
        "citizen": ["Parents join the SMC", "Report with photos and the school name/code"]}),
    (("pollution", "smoke", "burning", "air quality", "tree", "heat"), {
        "causes": ["Open burning of waste or crop residue", "Dust, traffic and industry", "Loss of green cover"],
        "prevention": ["Stop open burning with penalties and better waste collection", "Dust control at construction sites",
                       "Tree plantation and protection plan; heat action plan for hot months"],
        "citizen": ["Report burning spots with time and place", "Support local plantation drives"]}),
]
GENERIC_SOLUTION = {
    "causes": ["Slow response and no follow-up", "Lack of data on repeat problems"],
    "prevention": ["Track every complaint to closure with a deadline", "Use complaint hot-spot maps to plan yearly budgets",
                   "Regular review meeting between the ward committee and the department"],
    "citizen": ["Report with a clear photo and location", "Follow up through the official portal and RTI"]}


def _lookup_solution(issue_type: str):
    text = (issue_type or "").lower()
    for keywords, info in SOLUTION_RULES:
        if any(k in text for k in keywords):
            return info
    return GENERIC_SOLUTION


# ---- complaint storage ---------------------------------------------------------------------------
def load_complaints() -> pd.DataFrame:
    if not os.path.exists(COMPLAINTS_FILE):
        return pd.DataFrame()
    rows = []
    with open(COMPLAINTS_FILE, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    return pd.DataFrame(rows)


# =============================================================================================
# TOOLS
# =============================================================================================
@tool
def get_app_state(request: str = "summary", config: RunnableConfig = None) -> str:
    """Show uploaded images (with size and whether they carry GPS), which AI models are
    available, and how many complaints are saved. Call this first when unsure."""
    sess = _session(config)
    lines = [f"Uploaded images ({len(sess['images'])}):"]
    for name, e in sess["images"].items():
        lines.append(f"  - {name}: {e['img'].size[0]}x{e['img'].size[1]}, GPS in photo: {'yes' if e['gps'] else 'no'}")
    if not sess["images"]:
        lines.append("  (none)")
    lines.append(f"Local photo classifier: {'ready' if CLASSIFIER is not None and CLASSIFIER.ready else 'not available'}")
    lines.append(f"Local object detector: {'ready' if DETECTOR is not None and DETECTOR.ready else 'not available'}")
    lines.append(f"Saved complaints: {len(load_complaints())}")
    return "\n".join(lines)


@tool
def check_image_quality(image_name: str = "", config: RunnableConfig = None) -> str:
    """Check whether an uploaded photo is usable as evidence: resolution, blur and brightness.
    Use this before relying on a photo, and tell the user how to retake it if it is poor."""
    key, entry = _find_image(_session(config), image_name)
    if key is None:
        return entry
    img = entry["img"]
    w, h = img.size
    g = img.convert("L")
    g.thumbnail((800, 800))
    a = np.asarray(g, dtype=np.float32)
    lap = 4 * a[1:-1, 1:-1] - a[:-2, 1:-1] - a[2:, 1:-1] - a[1:-1, :-2] - a[1:-1, 2:]
    sharp = float(lap.var())
    bright = float(a.mean())
    issues = []
    if min(w, h) < 480:
        issues.append("resolution is low")
    if sharp < 60:
        issues.append("photo looks blurry")
    if bright < 60:
        issues.append("photo is too dark")
    elif bright > 205:
        issues.append("photo is overexposed")
    verdict = "Good quality." if not issues else "Problems: " + ", ".join(issues) + "."
    return (f"{key}: {w}x{h}px, sharpness score {sharp:.0f} (below 60 means blurry), "
            f"brightness {bright:.0f}/255. {verdict}")


@tool
def extract_image_location(image_name: str = "", config: RunnableConfig = None) -> str:
    """Read GPS coordinates stored inside a photo (EXIF). Use it to fill in the complaint
    location when the user did not give one. Many photos have no GPS."""
    key, entry = _find_image(_session(config), image_name)
    if key is None:
        return entry
    if not entry["gps"]:
        return f"{key} has no GPS data. Ask the user for the area, landmark or pin on the map."
    lat, lng = entry["gps"]
    return f"{key}: GPS {lat}, {lng} (https://www.openstreetmap.org/?mlat={lat}&mlon={lng}). Ask the user to confirm it."


@tool
def classify_image(image_name: str = "", config: RunnableConfig = None) -> str:
    """Use the trained local classifier to decide which civic category a photo shows
    (climate, healthcare, education, sanitation, infrastructure) or 'other' (not a civic problem)."""
    key, entry = _find_image(_session(config), image_name)
    if key is None:
        return entry
    if CLASSIFIER is None or not CLASSIFIER.ready:
        return "The local classifier is not available. Use describe_image instead."
    label, conf, probs = CLASSIFIER.predict(entry["img"])
    top = sorted(probs.items(), key=lambda kv: -kv[1])[:3]
    note = "This does NOT look like a civic problem." if label == "other" or conf < CLASSIFIER_MIN_CONF else ""
    return f"{key}: {label} ({conf:.0%}). Top 3: " + ", ".join(f"{k} {v:.0%}" for k, v in top) + f". {note}"


@tool
def detect_objects(image_name: str = "", min_confidence: float = 0.25, config: RunnableConfig = None) -> str:
    """Run the object detector (potholes, garbage, waterlogging) on a photo. The photo with
    boxes drawn is shown to the user. Returns what was found, an estimated severity and the
    department that normally handles it."""
    sess = _session(config)
    key, entry = _find_image(sess, image_name)
    if key is None:
        return entry
    if DETECTOR is None or not DETECTOR.ready:
        return "The local object detector is not available. Use describe_image instead."
    dets = [d for d in DETECTOR.detect(entry["img"], conf=min_confidence)]
    if not dets:
        return f"{key}: nothing detected above {min_confidence:.0%} confidence."
    img = entry["img"].copy()
    w, h = img.size
    draw = ImageDraw.Draw(img)
    for d in dets:
        x1, y1, x2, y2 = d["box"][0] * w, d["box"][1] * h, d["box"][2] * w, d["box"][3] * h
        draw.rectangle([x1, y1, x2, y2], outline=(220, 40, 40), width=max(2, w // 250))
        draw.text((x1 + 4, y1 + 4), f"{d['label']} {d['confidence']:.0%}", fill=(255, 255, 0))
    _queue_image(sess, img, f"Detections in {key}")
    sev = _severity_from(dets)
    depts = sorted({DEPT_BY_LABEL[d["label"]] for d in dets if d["label"] in DEPT_BY_LABEL})
    found = "; ".join(f"{d['label']} {d['confidence']:.0%} (covers {d['area_ratio']:.0%} of the photo)" for d in dets[:8])
    return (f"{key}: {len(dets)} object(s): {found}. Estimated severity {sev:.2f} out of 1 "
            f"(Low <0.4, Medium 0.4-0.7, High >0.7). Usually handled by: {', '.join(depts) or 'depends on the category'}.")


@tool
def describe_image(image_name: str = "",
                   question: str = "What civic problem is visible? Which of climate, healthcare, education, sanitation or infrastructure is it, and how serious does it look?",
                   config: RunnableConfig = None) -> str:
    """Ask a vision model about a photo. Use it for anything the local models cannot answer,
    or when they are not available. Be factual and say what is NOT visible."""
    key, entry = _find_image(_session(config), image_name)
    if key is None:
        return entry
    try:
        llm = ChatGroq(model=VISION_MODEL, temperature=0)
        msg = HumanMessage(content=[
            {"type": "text", "text": question + " Answer briefly and only from what is visible in the photo."},
            {"type": "image_url", "image_url": {"url": _to_data_url(entry["img"])}},
        ])
        return _clip(f"{key}: " + str(llm.invoke([msg]).content))
    except Exception as e:
        return f"Vision model error ({VISION_MODEL}): {e}"


@tool
def enhance_image(image_name: str,
                  operation: Literal["auto_contrast", "sharpen", "brighten", "resize", "rotate_90"] = "auto_contrast",
                  config: RunnableConfig = None) -> str:
    """Improve or fix a photo and keep the result as a new image.
    auto_contrast - fix washed-out or dark photos | sharpen - mild sharpening
    brighten - 30% brighter | resize - shrink so the longest side is 1280px (faster upload)
    rotate_90 - rotate a sideways photo. The new image is shown to the user."""
    sess = _session(config)
    key, entry = _find_image(sess, image_name)
    if key is None:
        return entry
    img = entry["img"]
    if operation == "auto_contrast":
        out = ImageOps.autocontrast(img, cutoff=1)
    elif operation == "sharpen":
        out = img.filter(ImageFilter.UnsharpMask(radius=2, percent=130, threshold=3))
    elif operation == "brighten":
        out = ImageEnhance.Brightness(img).enhance(1.3)
    elif operation == "resize":
        out = img.copy()
        out.thumbnail((1280, 1280))
    else:
        out = img.rotate(-90, expand=True)
    new_name = f"{os.path.splitext(key)[0]}_{operation}"
    n = 2
    base = new_name
    while new_name in sess["images"]:
        new_name = f"{base}_{n}"
        n += 1
    sess["images"][new_name] = {"img": out, "gps": entry["gps"]}
    _queue_image(sess, out, f"{new_name}")
    return f"Created '{new_name}' ({out.size[0]}x{out.size[1]}) from '{key}' using {operation}. GPS kept: {'yes' if entry['gps'] else 'no'}."


@tool
def check_text_safety(text: str) -> str:
    """Check a citizen's message for abusive language and links. Call it on the message before
    saving a complaint. If it fails, politely ask the user to rephrase."""
    ok, reason = _text_ok(text)
    return "OK: the text is acceptable." if ok else f"NOT OK: {reason}"


@tool
def save_structured_complaint(
    category: Literal["Climate", "Healthcare", "Education", "Sanitation", "Infrastructure"],
    issue_type: str,
    problem: str,
    suggested_action: str,
    original_text: str,
    language: str = "English",
    duration: str = "",
    location: str = "",
    severity: Literal["Low", "Medium", "High"] = "Medium",
    image_names: str = "",
    config: RunnableConfig = None,
) -> str:
    """Save a structured complaint made from the citizen's message.
    category: one of the five categories.
    issue_type: short English label, e.g. 'garbage not collected', 'pothole', 'waterlogging'.
    problem: one clear English sentence.
    suggested_action: what should happen, e.g. 'Route to the municipal sanitation team'.
    original_text: the citizen's exact words (any language).
    language: language of the original text.
    duration: how long it has been going on, e.g. '5 days'; empty if unknown.
    location: area/landmark as given by the user; leave empty if unknown. NEVER invent one.
    severity: Low, Medium or High.
    image_names: comma separated names of uploaded photos that show the problem (optional).
    Rejects abusive text and photos that do not show a civic problem."""
    sess = _session(config)

    for t in (original_text, problem):
        ok, reason = _text_ok(t)
        if not ok:
            return f"NOT SAVED: {reason} Ask the user to rephrase."

    names, lat, lng = [], None, None
    for raw in [n.strip() for n in image_names.split(",") if n.strip()]:
        key, entry = _find_image(sess, raw)
        if key is None:
            return f"NOT SAVED: {entry}"
        if CLASSIFIER is not None and CLASSIFIER.ready:
            label, conf, _ = CLASSIFIER.predict(entry["img"])
            if label == "other" or conf < CLASSIFIER_MIN_CONF:
                return f"NOT SAVED: '{key}' does not look like a civic problem. Ask for a clearer photo of the issue."
        names.append(key)
        if lat is None and entry["gps"]:
            lat, lng = entry["gps"]

    location = location.strip()
    if not location and lat is not None:
        location = f"GPS from photo: {lat}, {lng} (to be confirmed by the user)"

    info = _lookup_authority(category, issue_type)
    rec = {
        "id": uuid.uuid4().hex[:8].upper(),
        "created_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
        "category": category, "issue_type": issue_type.strip(), "problem": problem.strip(),
        "duration": duration.strip(), "location": location, "latitude": lat, "longitude": lng,
        "suggested_action": suggested_action.strip(), "authority": info["authority"],
        "severity": severity, "language": language, "original_text": original_text.strip(), "images": names,
    }
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(COMPLAINTS_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    return (f"Complaint saved. ID: {rec['id']}\n"
            f"Category: {category}\nProblem: {rec['problem']}\n"
            f"Duration: {rec['duration'] or 'Not stated'}\n"
            f"Location: {location or 'To be supplied or confirmed by the user'}\n"
            f"Suggested action: {rec['suggested_action']}\nRoute to: {info['authority']}\n"
            f"Severity: {severity}\nPhotos attached: {', '.join(names) or 'none'}")


@tool
def find_authority(category: Literal["Climate", "Healthcare", "Education", "Sanitation", "Infrastructure"],
                   issue_type: str, city: str = "") -> str:
    """Find which authority handles a problem, how to reach it, and where to escalate.
    Use this answer instead of guessing. issue_type is a short label like 'pothole' or 'garbage'."""
    info = _lookup_authority(category, issue_type)
    out = [f"Authority: {info['authority']}", "Where to report:"]
    out += [f"  - {c}" for c in info["channels"]]
    out.append(f"If not resolved, escalate to: {info['escalate']}")
    out.append(GENERAL_NOTE)
    if city:
        out.append(f"City given: {city}. Tell the user to look up the {city} municipal / department website for the exact helpline.")
    return "\n".join(out)


@tool
def suggest_long_term_solutions(category: Literal["Climate", "Healthcare", "Education", "Sanitation", "Infrastructure"],
                                issue_type: str) -> str:
    """Return likely root causes and long-term prevention measures for a recurring problem,
    plus what citizens can do. Use it to write a practical prevention plan."""
    s = _lookup_solution(issue_type)
    return ("Likely root causes:\n" + "\n".join(f"  - {x}" for x in s["causes"]) +
            "\nLong-term prevention:\n" + "\n".join(f"  - {x}" for x in s["prevention"]) +
            "\nWhat citizens / RWAs can do:\n" + "\n".join(f"  - {x}" for x in s["citizen"]))


@tool
def generate_area_report(area: str = "all", last_n_days: int = 30) -> str:
    """Summarise saved complaints for an area (matched against the location text) over the
    last N days: totals, categories, top issues, severity and authorities. Use the numbers to
    write a short area-level report for officials."""
    df = load_complaints()
    if df.empty:
        return "No complaints have been saved yet."
    df["created_at"] = pd.to_datetime(df["created_at"], errors="coerce", utc=True)
    df = df[df["created_at"] >= datetime.now(timezone.utc) - timedelta(days=last_n_days)]
    if area.strip().lower() not in ("", "all"):
        df = df[df["location"].fillna("").str.contains(area.strip(), case=False, regex=False)]
    if df.empty:
        return f"No complaints found for '{area}' in the last {last_n_days} days."
    cat = df["category"].value_counts()
    issues = df["issue_type"].str.lower().value_counts().head(5)
    sev = df["severity"].value_counts()
    auth = df["authority"].value_counts().head(5)
    long_pending = df[df["duration"].fillna("").str.len() > 0][["issue_type", "duration", "location"]].head(5)
    return _clip(
        f"Area: {area} | last {last_n_days} days | complaints: {len(df)}\n"
        f"By category:\n{cat.to_string()}\nTop issues:\n{issues.to_string()}\n"
        f"Severity:\n{sev.to_string()}\nAuthorities involved:\n{auth.to_string()}\n"
        f"Stated durations (sample):\n{long_pending.to_string(index=False) if not long_pending.empty else 'none'}")


all_tools = [
    get_app_state, check_image_quality, extract_image_location, classify_image, detect_objects,
    describe_image, enhance_image, check_text_safety, save_structured_complaint,
    find_authority, suggest_long_term_solutions, generate_area_report,
]

system_prompt = """You are NAGRIC AI, a civic assistant for citizens in India. Citizens write in English,
Hindi, Hinglish or other Indian languages. Reply in the same language and script the citizen used.
Keep structured fields in English (except original_text, which stays exactly as written).
Use your tools; never invent facts, authorities, phone numbers or locations.

Tools:
- save_structured_complaint: turn a citizen's message into a structured complaint
  (category, issue_type, problem, duration, location, suggested_action, severity).
- find_authority: which authority handles it, where to report, how to escalate.
- suggest_long_term_solutions: root causes and prevention plan.
- generate_area_report: short area-level report from saved complaints.
- Photo tools: get_app_state, check_image_quality, extract_image_location, classify_image,
  detect_objects, describe_image, enhance_image.
- check_text_safety: check a message for abusive language or links.

Workflow for a complaint:
1. Call check_text_safety on the message. If it fails, politely ask the citizen to rephrase.
2. Pick the category from: Climate, Healthcare, Education, Sanitation, Infrastructure.
3. If photos are mentioned or available, run check_image_quality, then classify_image or
   describe_image; use detect_objects for potholes, garbage and waterlogging.
   If a photo does not show a civic problem, say so and do not attach it.
4. Location: use what the citizen said. If missing, try extract_image_location and ask the citizen
   to confirm. If still unknown, leave it empty and ask for it. Never guess a location.
5. Call save_structured_complaint, then find_authority, then (when asked, or when the problem keeps
   coming back) suggest_long_term_solutions.
6. Present the result clearly: the structured complaint, who to contact and how, and the long-term plan.

Rules:
- If the citizen only asks a question (for example which office to approach), answer it with
  find_authority without saving a complaint.
- Photos are listed at the end of the user's message as [Images available: ...]; use those exact names.
- If a tool says NOT SAVED or reports an error, tell the citizen honestly and what to do next.
- Say that the official office or helpline should be verified locally, because they differ by city.
- Emergencies (fire, injury, flooding with danger): tell them to call 112 first, and 108 for an ambulance.
"""


@st.cache_resource
def get_agent():
    llm = ChatGroq(model=TEXT_MODEL, temperature=0)
    return create_agent(model=llm, tools=all_tools, system_prompt=system_prompt, checkpointer=InMemorySaver())


def run_agent(query: str) -> str:
    try:
        res = get_agent().invoke(
            {"messages": [{"role": "user", "content": query}]},
            config={"configurable": {"thread_id": st.session_state["thread_id"]}},
        )
        content = res["messages"][-1].content
        return content if isinstance(content, str) else str(content)
    except Exception as e:
        return f"Something went wrong while running the agent: {e}"


# =============================================================================================
# STREAMLIT UI
# =============================================================================================
EXAMPLES = [
    "Hamare area mein pichle 5 din se kachra nahi uthaya gaya hai.",
    "There is a big pothole near the school gate on our main road. Who should I report it to?",
    "Every monsoon our lane gets waterlogged. How do we stop this for good?",
    "Write a short report of all complaints this month.",
]


def add_uploads(sess, files):
    for f in files[:MAX_IMAGES]:
        k = f"{f.name}-{f.size}"
        if k in sess["seen"] or len(sess["images"]) >= MAX_IMAGES:
            continue
        try:
            img = Image.open(f)
            gps = _gps_from_exif(img)                       # read GPS before the image is rotated/copied
            img = ImageOps.exif_transpose(img).convert("RGB")
            img.thumbnail((2000, 2000))
        except Exception:
            st.sidebar.warning(f"Could not read {f.name}.")
            sess["seen"].add(k)
            continue
        name, n = f.name, 2
        while name in sess["images"]:
            name = f"{os.path.splitext(f.name)[0]}_{n}{os.path.splitext(f.name)[1]}"
            n += 1
        sess["images"][name] = {"img": img, "gps": gps}
        sess["seen"].add(k)


def main():
    st.set_page_config(page_title="NAGRIK AI Assistant", layout="wide")
    st.header("NAGRIK AI: Civic Problem Assistant")
    st.session_state.setdefault("messages", [])
    st.session_state.setdefault("thread_id", str(uuid.uuid4()))
    st.session_state.setdefault("uploader_n", 0)

    if not os.getenv("GROQ_API_KEY"):
        st.error("GROQ_API_KEY is missing. Add it to a .env file next to this script and restart.")
        st.stop()

    sess = SESSIONS.setdefault(st.session_state["thread_id"], _new_session())

    with st.sidebar:
        st.subheader("Photos of the problem")
        files = st.file_uploader("Upload photos", type=["jpg", "jpeg", "png", "webp"],
                                 accept_multiple_files=True, key=f"up_{st.session_state['uploader_n']}")
        if files:
            add_uploads(sess, files)
        for name, e in sess["images"].items():
            st.image(e["img"], caption=f"{name}" + (" (GPS)" if e["gps"] else ""), width=140)
        if sess["images"] and st.button("Clear photos"):
            sess["images"].clear()
            sess["seen"].clear()
            st.session_state["uploader_n"] += 1
            st.rerun()

        st.subheader("Try an example")
        for i, ex in enumerate(EXAMPLES):
            if st.button(ex[:46] + ("..." if len(ex) > 46 else ""), key=f"ex{i}"):
                st.session_state["queued_query"] = ex

        st.caption(f"Classifier: {'on' if CLASSIFIER is not None and CLASSIFIER.ready else 'off'} | "
                   f"Detector: {'on' if DETECTOR is not None and DETECTOR.ready else 'off'}")

    df = load_complaints()
    with st.expander(f"Saved complaints ({len(df)})", expanded=False):
        if df.empty:
            st.caption("Nothing saved yet.")
        else:
            show = ["id", "created_at", "category", "issue_type", "problem", "duration", "location", "severity", "authority"]
            st.dataframe(df[[c for c in show if c in df.columns]])
            c1, c2 = st.columns(2)
            c1.download_button("Download CSV", df.to_csv(index=False).encode("utf-8"), "complaints.csv", "text/csv")
            c2.download_button("Download JSON", df.to_json(orient="records", force_ascii=False).encode("utf-8"),
                               "complaints.json", "application/json")

    for m in st.session_state["messages"]:
        with st.chat_message(m["role"]):
            st.markdown(m["content"])
            for im in m.get("images", []):
                st.image(im["bytes"], caption=im["caption"])

    query = st.chat_input("Describe a problem in your area (any language)") or st.session_state.pop("queued_query", None)
    if query:
        st.chat_message("user").markdown(query)
        st.session_state["messages"].append({"role": "user", "content": query})
        agent_query = query
        if sess["images"]:
            agent_query += f"\n\n[Images available: {', '.join(sess['images'])}]"
        sess["pending"] = []
        with st.spinner("Working on it..."):
            answer = run_agent(agent_query)
        pending, sess["pending"] = list(sess["pending"]), []
        st.session_state["messages"].append({"role": "assistant", "content": answer, "images": pending})
        st.rerun()


if __name__ == "__main__":
    main()