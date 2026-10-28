import math
import os
import pickle

from flask import Flask, jsonify, render_template, request

from preprocess import preprocess_text

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_DIR = os.path.join(BASE_DIR, "model")
MAX_CHARS = 2000


def load_pickle(filename):
    path = os.path.join(MODEL_DIR, filename)
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"Missing {path}. Put model.pkl and vectorizer.pkl inside the 'model' folder."
        )
    with open(path, "rb") as f:
        return pickle.load(f)


# Loaded once at startup, not on every request
model = load_pickle("model.pkl")
vectorizer = load_pickle("vectorizer.pkl")

app = Flask(__name__)


def classify(text: str) -> dict:
    cleaned = preprocess_text(text)
    if not cleaned:
        # Only stopwords / symbols / numbers: the vector would be all zeros
        return {"label": "unclear", "confidence": None}

    features = vectorizer.transform([cleaned])
    score = float(model.decision_function(features)[0])  # > 0 means "bad"
    label = "bad" if score > 0 else "good"

    # LinearSVC has no predict_proba, so this is a rough strength indicator (50-100%),
    # not a calibrated probability.
    confidence = 1 / (1 + math.exp(-abs(score)))
    return {"label": label, "confidence": round(confidence, 3), "score": round(score, 3)}


@app.get("/")
def home():
    return render_template("index.html", max_chars=MAX_CHARS)


@app.post("/predict")
def predict():
    data = request.get_json(silent=True) or {}
    message = str(data.get("message", "")).strip()

    if not message:
        return jsonify(error="Enter a message to check."), 400
    if len(message) > MAX_CHARS:
        return jsonify(error=f"Messages can be at most {MAX_CHARS} characters."), 400

    return jsonify(classify(message))


@app.get("/health")
def health():
    return jsonify(status="ok")


if __name__ == "__main__":
    app.run(debug=True)
