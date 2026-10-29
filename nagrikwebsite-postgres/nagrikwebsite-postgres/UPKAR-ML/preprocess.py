"""Text preprocessing. Must stay IDENTICAL to the cleaning code in the training notebook,
otherwise the model sees different features at prediction time than it did in training."""
import re

import nltk
from nltk.corpus import stopwords
from nltk.stem.porter import PorterStemmer

try:
    nltk.data.find("corpora/stopwords")
except LookupError:
    nltk.download("stopwords", quiet=True)

_stemmer = PorterStemmer()
ENGLISH_STOPWORDS = set(stopwords.words("english"))
HINDI_STOPWORDS = {
    "और", "का", "की", "के", "है", "हैं", "था", "थी",
    "थे", "को", "से", "में", "पर", "यह", "वह", "एक",
    "कर", "रहा", "रही", "रहे", "लिए", "तो",
    "भी", "तक", "अपने", "अपनी", "बहुत", "अगर", "लेकिन",
}


def preprocess_text(text: str) -> str:
    # Keep English letters, Hindi (Devanagari) and spaces
    review = re.sub(r"[^a-zA-Z\u0900-\u097F\s]", " ", str(text))
    review = review.lower()

    processed = []
    for word in review.split():
        if word in ENGLISH_STOPWORDS or word in HINDI_STOPWORDS:
            continue
        # Porter stemming applies to English words only
        if re.fullmatch(r"[a-z]+", word):
            word = _stemmer.stem(word)
        processed.append(word)

    return " ".join(processed)