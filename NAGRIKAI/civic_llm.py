"""
NAGRIK AI - Civic Problem Intelligence & Groq LLM Engine
Specialized for National Capital Territory of Delhi (GNCTD, MCD, PWD, DJB, DPCC, DoE, DHS).
Directly integrates Groq API with robust fallbacks and high-accuracy Delhi civic routing.
"""
import os
import re
import uuid
import json
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv

# Load environment variables (.env)
load_dotenv(override=True)

import database

# Groq API configuration
DEFAULT_KEY = ""  # set GROQ_API_KEY in environment / .env (never hardcode)
GROQ_API_KEY = os.getenv("GROQ_API_KEY", DEFAULT_KEY).strip().strip('"').strip("'")
PRIMARY_MODEL = os.getenv("GROQ_MODEL", "qwen/qwen3.8-27b").strip().strip('"').strip("'")
FALLBACK_MODELS = [
    "qwen/qwen3.8-27b",
    "allam-2-7b",
    "llama-3.3-70b-versatile",
    "llama-3.1-8b-instant",
    "llama3-70b-8192",
    "llama3-8b-8192",
    "mixtral-8x7b-32768",
    "openai/gpt-oss-120b",
    "openai/gpt-oss-20b"
]


def get_groq_client():
    """Returns an initialized Groq client or None if API key missing."""
    key = os.getenv("GROQ_API_KEY", GROQ_API_KEY).strip().strip('"').strip("'")
    if not key:
        return None
    try:
        from groq import Groq
        return Groq(api_key=key)
    except Exception as e:
        print(f"Error initializing Groq client: {e}")
        return None


def test_groq_connection() -> dict:
    """Verifies Groq API connectivity and returns working model details."""
    client = get_groq_client()
    if not client:
        return {"connected": False, "error": "No Groq API key configured in .env"}

    models_to_try = [PRIMARY_MODEL] + [m for m in FALLBACK_MODELS if m != PRIMARY_MODEL]
    for model in models_to_try:
        try:
            resp = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "You are a civic assistant."},
                    {"role": "user", "content": "Reply with exactly: OK"}
                ],
                max_tokens=20,
                temperature=0.1
            )
            content = (resp.choices[0].message.content or "").strip()
            if content:
                return {
                    "connected": True,
                    "model": model,
                    "response": content,
                    "api_key_configured": True
                }
        except Exception as e:
            continue

    return {"connected": False, "error": "Unable to receive response from Groq models."}


def generate_delhi_ai_solution(title: str, description: str, location: str, category: str) -> dict:
    """
    Calls Groq LLM to generate an authoritative civic resolution specifically grounded
    in Delhi municipal and GNCTD frameworks (MCD, PWD Delhi, DJB, DPCC, DoE, DGHS).
    """
    client = get_groq_client()
    if client:
        system_prompt = (
            "You are NAGRIK AI Delhi Municipal Grievance and Legal Authority AI. "
            "You provide definitive, legal, and operational solutions for citizen complaints in Delhi (NCT of Delhi). "
            "Always reference actual Delhi authorities (e.g., MCD Zonal Offices, PWD Delhi, Delhi Jal Board, DPCC, DoE Delhi, DGHS Delhi, Traffic Police), "
            "specific Delhi legislation (DMC Act 1957, Delhi Right to Service e-SLA Act 2011, Delhi Water Board Act 1998, CAQM GRAP Rules, Delhi Preservation of Trees Act 1994), "
            "official helplines (MCD 311 / 155304, DJB 1916, PWD 1800110093, Green Delhi App, 112), and realistic resolution SLA timelines."
        )

        user_prompt = f"""Analyze this civic complaint from Delhi:
Category: {category}
Title: {title}
Location: {location}
Description: {description}

Provide a concise, highly practical resolution in JSON format with exactly these keys:
{{
  "solution": "Clear step-by-step resolution for citizens and municipal engineers under Delhi rules (max 3 sentences).",
  "authority": "Designated department and zonal wing in Delhi.",
  "rules": "Specific Delhi statutory act, rule, or high court guideline.",
  "sla": "Standard turnaround timeline under Delhi Right to Service (e-SLA) or municipal charter."
}}
Return ONLY valid raw JSON."""

        models_to_try = [PRIMARY_MODEL] + [m for m in FALLBACK_MODELS if m != PRIMARY_MODEL]
        for model in models_to_try:
            try:
                response = client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    temperature=0.2,
                    max_tokens=450
                )
                text = (response.choices[0].message.content or "").strip()
                if not text:
                    # Model returned empty text, try next
                    continue

                # Parse JSON if possible
                json_match = re.search(r"\{.*\}", text, re.DOTALL)
                if json_match:
                    parsed = json.loads(json_match.group(0))
                    return {
                        "solution": parsed.get("solution", text),
                        "authority": parsed.get("authority", "Municipal Corporation of Delhi (MCD) / PWD"),
                        "rules": parsed.get("rules", "Delhi Right to Service Act 2011 & DMC Act 1957"),
                        "sla": parsed.get("sla", "48 to 72 hours"),
                        "model": model
                    }
                else:
                    return {
                        "solution": text,
                        "authority": "MCD / Delhi PWD / DJB",
                        "rules": "Delhi Municipal Bye-laws & e-SLA Act",
                        "sla": "48 hours",
                        "model": model
                    }
            except Exception as e:
                print(f"Groq generation error with model {model}: {e}")
                continue

    # Fallback: High accuracy rule-based Delhi municipal knowledge
    return get_local_delhi_solution(category, title, description, location)


def get_local_delhi_solution(category: str, title: str, description: str, location: str) -> dict:
    """Local high-precision fallback for Delhi municipal framework."""
    cat = (category or "").lower()
    text = f"{title} {description}".lower()

    if "sanitation" in cat or any(w in text for w in ["garbage", "kachra", "waste", "trash", "dustbin", "dhalao", "safai"]):
        return {
            "solution": "Lodge an instant grievance on the MCD 311 Mobile App with geo-tagged photograph. Under Section 353 of the Delhi Municipal Corporation Act 1957, the Zonal Sanitation Superintendent is obligated to mobilize mechanical compactors and clear secondary waste within 24 to 48 hours.",
            "authority": "Municipal Corporation of Delhi (MCD) - Solid Waste Management & Sanitation Wing",
            "rules": "DMC Act 1957 Sec 353, Solid Waste Management Rules 2016, Swachh Bharat Urban SLA",
            "sla": "24 to 48 Hours",
            "model": "delhi_civic_engine"
        }
    elif "infrastructure" in cat or any(w in text for w in ["pothole", "road", "street light", "light", "drain", "water", "pipe", "bridge"]):
        if any(w in text for w in ["water", "pipe", "leak", "jal"]):
            return {
                "solution": "Notify the Delhi Jal Board (DJB) Central Emergency Control Room at 1916 or through the DJB M-Seva portal. Under the Delhi Water Board Act 1998, hydraulic isolation and pipe sleeve replacement must be initiated within 12 hours to prevent contamination and road sinking.",
                "authority": "Delhi Jal Board (DJB) - Zonal Distribution & Maintenance Division",
                "rules": "Delhi Water Board Act 1998 Section 34 (Waste Prevention & Main Repair)",
                "sla": "12 to 24 Hours",
                "model": "delhi_civic_engine"
            }
        elif any(w in text for w in ["light", "dark", "lamp", "pole"]):
            return {
                "solution": "Report the pole number and street junction via the MCD 311 App or respective power DISCOM (BSES Rajdhani/Yamuna or TPDDL) helpline. Under Delhi Electricity Regulatory Commission (DERC) Standards, community street lighting circuits must be repaired within 48 hours.",
                "authority": "MCD Electrical Engineering Division & Zonal DISCOM Streetlight Cell",
                "rules": "DERC Standards of Performance Regulations & DMC Electrical Norms",
                "sla": "24 to 48 Hours",
                "model": "delhi_civic_engine"
            }
        else:
            return {
                "solution": "Register urgent road defect on PWD Delhi Sewa portal (or call 1800-11-0093 for arterial roads; MCD 311 for colony roads). As mandated by the Delhi Right to Service (e-SLA) Act 2011, road potholes must be filled with IRC:82 compliant asphalt mix within 72 hours.",
                "authority": "Public Works Department (PWD Delhi) / MCD Road Division",
                "rules": "Delhi Right to Service (e-SLA) Act 2011 & IRC:82 Guidelines",
                "sla": "72 Hours",
                "model": "delhi_civic_engine"
            }
    elif "education" in cat or any(w in text for w in ["school", "desk", "teacher", "classroom", "student"]):
        return {
            "solution": "Submit immediate petition to the School Management Committee (SMC) Chairperson and the Directorate of Education (DoE) Samagra Shiksha portal. Emergency civil, sanitary, or furniture repairs must be inspected by PWD Education Cell within 5 working days.",
            "authority": "Directorate of Education (DoE Delhi) & PWD Education Building Division",
            "rules": "Delhi School Education Act & Rules 1973 (DSEAR) & RTE Act 2009 Sec 19",
            "sla": "5 to 7 Days",
            "model": "delhi_civic_engine"
        }
    elif "healthcare" in cat or any(w in text for w in ["hospital", "clinic", "medicine", "doctor", "dispensary", "mohalla"]):
        return {
            "solution": "Escalate stockout or diagnostic downtime to the Chief District Medical Officer (CDMO) and the Mohalla Clinic Central Nodal Cell. The Central Procurement Agency (CPA), GNCTD is obligated to dispatch emergency buffer medicines within 48 hours.",
            "authority": "Directorate General of Health Services (DGHS Delhi) / Mohalla Clinic Cell",
            "rules": "GNCTD Essential Drug List (DEL-NLEM) Protocol & Hospital Citizens Charter",
            "sla": "48 Hours",
            "model": "delhi_civic_engine"
        }
    else:  # Climate / Pollution
        return {
            "solution": "Upload geo-tagged evidence to the Green Delhi Mobile App (managed directly by DPCC & CAQM). Under statutory GRAP notifications, open biomass burning or unmitigated construction dust attracts immediate spot fines ranging from ₹5,000 to ₹50,000.",
            "authority": "Delhi Pollution Control Committee (DPCC) & CAQM Air Enforcement Flying Squad",
            "rules": "Air (Prevention and Control of Pollution) Act 1981 & CAQM Statutory Directions",
            "sla": "24 Hours",
            "model": "delhi_civic_engine"
        }


def query_assistant(query: str, user_id: int = 1, session_id: str = "default") -> dict:
    """
    Civic conversational assistant powered by Groq LLM with fallbacks.
    Answers citizens' queries in English, Hindi, or Hinglish with accurate Delhi municipal guidance.
    """
    client = get_groq_client()
    if client:
        system_prompt = (
            "You are NAGRIK AI, an intelligent civic assistant for citizens residing in the National Capital Territory of Delhi, India. "
            "You help citizens identify the exact responsible government agency (MCD, PWD Delhi, Delhi Jal Board, DPCC, DoE Delhi, DGHS, Delhi Police), "
            "official helplines (MCD 311, DJB 1916, PWD 1800110093, Green Delhi App, 112, 1077), and advise on citizens' rights under Delhi laws. "
            "Respond helpfully in whatever language the citizen uses (English, Hindi, or Hinglish). Keep answers polite, concise, and structured with bullet points."
        )

        models_to_try = [PRIMARY_MODEL] + [m for m in FALLBACK_MODELS if m != PRIMARY_MODEL]
        for model in models_to_try:
            try:
                response = client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": query}
                    ],
                    temperature=0.3,
                    max_tokens=600
                )
                reply = (response.choices[0].message.content or "").strip()
                if not reply:
                    continue

                return {
                    "reply": reply,
                    "type": "groq_assistant",
                    "model": model,
                    "session_id": session_id
                }
            except Exception as e:
                print(f"Groq chat assistant error with {model}: {e}")
                continue

    # Rule-based fallback if Groq call is offline or throttled
    reply = (
        f"**Namaste! NAGRIK AI Civic Guide (Delhi Zone)**\n\n"
        f"Regarding your query: *\"{query}\"*\n\n"
        f"• **Designated Authority**: Municipal Corporation of Delhi (MCD) / Public Works Department (PWD Delhi) / Delhi Jal Board (DJB).\n"
        f"• **Recommended Action**: For immediate registration with geo-tagging, download the **MCD 311 App** or the **Green Delhi App**.\n"
        f"• **Emergency Helplines**:\n"
        f"  - MCD Civic Control: **155304**\n"
        f"  - Delhi Jal Board: **1916**\n"
        f"  - PWD Delhi Pothole Toll-Free: **1800-11-0093**\n"
        f"  - Central Grievance: **pgportal.gov.in (CPGRAMS)** or CM Grievance Cell.\n"
        f"• **Resolution SLA**: 24-72 hours under Delhi Right to Service Act 2011."
    )
    return {
        "reply": reply,
        "type": "local_assistant",
        "model": "local_rule_engine",
        "session_id": session_id
    }
