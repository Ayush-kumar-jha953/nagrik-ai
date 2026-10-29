import os
import re

# ---- Hard blocklist: explicit abusive slurs/profanity ONLY ----
# These are the only words that should actually block a post.
ABUSIVE_KEYWORDS = {
    "madarchod", "bhenchod", "behenchod", "bhosdike", "chutiya", "gandu",
    "harami", "kamine", "randi", "bhadwe",
    "fuck", "bitch", "asshole", "bastard", "motherfucker", "fucker",
    "cunt", "nigger", "slut", "whore"
}

# Civic / official terms that must NEVER be blocked
CIVIC_SAFE_WORDS = {
    "pothole", "garbage", "trash", "sewage", "drain", "nala", "streetlight",
    "water", "pipe", "leak", "road", "footpath", "bridge", "school", "teacher",
    "hospital", "clinic", "medicine", "mosquito", "pollution", "dust", "smoke",
    "construction", "accident", "repair", "broken", "missing", "flooding",
    "manhole", "sewer", "kachra", "safai", "naali", "bijli", "pani", "sadak",
    "stagnant", "colony", "sector", "block", "ward", "delhi", "mcd", "pwdpe",
    "djb", "dpcc", "education", "healthcare", "sanitation", "infrastructure",
    "holes", "hole", "near", "school", "area", "problem", "issue", "complaint",
    "overflowing", "blocked", "dark", "broken", "damaged", "missing", "stray",
    "smell", "odour", "fire", "hazard", "illegal", "encroachment", "park",
    "market", "gate", "corner", "cross", "junction", "lane", "gali", "plot",
}

# Categories of spam/non-civic content (checked only when no civic keywords present)
SPAM_PATTERNS = [
    r"(?:https?://|www\.)\S+",            # URLs / links
    r"\b(?:click here|buy now|free cash|earn money|win prize|claim reward)\b",
    r"\b(?:whatsapp|telegram)\s+(?:group|channel|link)\b",
]


def moderate_text(text: str) -> dict:
    """
    Evaluates civic post text for genuine abuse / spam.
    
    Logic (in priority order):
    1. Empty → reject
    2. Explicit abusive slur word found → reject
    3. URL/spam pattern found → reject  
    4. Has at least one civic/location keyword → APPROVE (civic posts always pass)
    5. Very short non-civic text that's also ambiguous → approve with low score
    6. Everything else → APPROVE (default permissive for citizen reports)
    
    Returns:
    {
        "flagged": bool,
        "label": "bad" | "good" | "unclear",
        "score": float,
        "confidence": float,
        "reason": str,
        "message": str
    }
    """
    text_str = str(text or "").strip()

    # 1. Empty check
    if not text_str or len(text_str) < 4:
        return {
            "flagged": True,
            "label": "unclear",
            "score": 0.0,
            "confidence": 0.0,
            "reason": "Empty post content.",
            "message": "Please provide a description of the civic issue."
        }

    lower = text_str.lower()
    tokens = set(re.findall(r"\b\w+\b", lower))

    # 2. Hard abusive keyword check (exact word-boundary matching only)
    for token in tokens:
        if token in ABUSIVE_KEYWORDS:
            return {
                "flagged": True,
                "label": "bad",
                "score": 1.0,
                "confidence": 0.99,
                "reason": "Abusive or derogatory language detected.",
                "message": (
                    "Your post cannot be posted. It contains abusive or offensive language. "
                    "Please express your civic grievance respectfully so authorities can act on it."
                )
            }

    # 3. URL / spam pattern check
    for pattern in SPAM_PATTERNS:
        if re.search(pattern, lower, re.I):
            return {
                "flagged": True,
                "label": "bad",
                "score": 1.0,
                "confidence": 1.0,
                "reason": "External links, URLs or promotional content are not permitted.",
                "message": (
                    "Your post cannot be posted. Links and promotional content are prohibited "
                    "in civic reports to prevent spam."
                )
            }

    # 4. If the text contains any civic/safe keyword → always approve
    if tokens & CIVIC_SAFE_WORDS:
        return {
            "flagged": False,
            "label": "good",
            "score": -0.5,
            "confidence": 0.95,
            "reason": "Civic issue content detected. Post approved.",
            "message": "Content moderation check passed."
        }

    # 5. Generic short text without civic terms — still approve
    #    (citizen might use non-standard terminology but still report a real issue)
    return {
        "flagged": False,
        "label": "good",
        "score": -0.1,
        "confidence": 0.75,
        "reason": "No abusive content detected. Post approved.",
        "message": "Content moderation check passed."
    }
