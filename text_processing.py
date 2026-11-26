"""Shared text normalization for model training and prediction."""
from __future__ import annotations

import re


_CONTRACTIONS = {
    "can't": "can not",
    "cannot": "can not",
    "couldn't": "could not",
    "didn't": "did not",
    "doesn't": "does not",
    "don't": "do not",
    "hadn't": "had not",
    "hasn't": "has not",
    "haven't": "have not",
    "isn't": "is not",
    "mustn't": "must not",
    "shouldn't": "should not",
    "wasn't": "was not",
    "weren't": "were not",
    "won't": "will not",
    "wouldn't": "would not",
    "ain't": "is not",
    # This corpus frequently stores contractions after punctuation stripping.
    "cant": "can not",
    "couldnt": "could not",
    "didnt": "did not",
    "doesnt": "does not",
    "dont": "do not",
    "hadnt": "had not",
    "hasnt": "has not",
    "havent": "have not",
    "isnt": "is not",
    "mustnt": "must not",
    "shouldnt": "should not",
    "wasnt": "was not",
    "werent": "were not",
    "wont": "will not",
    "wouldnt": "would not",
}
_SPLIT_CONTRACTIONS = {
    "can t": "can not",
    "couldn t": "could not",
    "didn t": "did not",
    "doesn t": "does not",
    "don t": "do not",
    "hadn t": "had not",
    "hasn t": "has not",
    "haven t": "have not",
    "isn t": "is not",
    "mustn t": "must not",
    "shouldn t": "should not",
    "wasn t": "was not",
    "weren t": "were not",
    "won t": "will not",
    "wouldn t": "would not",
}
_NEGATION_CUES = {"not", "no", "never", "hardly", "barely", "rarely", "seldom", "without"}
_CLAUSE_BREAKS = {"but", "however", "though", "although", "yet", "nevertheless"}
_PUNCTUATION = {".", "!", "?", ",", ";", ":"}
_TOKEN_PATTERN = re.compile(r"[a-z]+(?:'[a-z]+)?|[.!?,;:]")


def normalize_negation(text: str, scope: int = 3) -> str:
    """Mark words within a short negation scope so TF-IDF distinguishes polarity.

    Punctuation and contrast clauses end the scope. Common contractions are
    expanded first, so phrases such as "don't feel happy" are handled too.
    """
    text = str(text).lower()
    for contraction, expanded in _SPLIT_CONTRACTIONS.items():
        text = re.sub(rf"\b{re.escape(contraction)}\b", expanded, text)
    for contraction, expanded in _CONTRACTIONS.items():
        text = re.sub(rf"\b{re.escape(contraction)}\b", expanded, text)

    tokens = _TOKEN_PATTERN.findall(text)
    normalized = []
    remaining = 0

    for index, token in enumerate(tokens):
        if token in _PUNCTUATION:
            normalized.append(token)
            remaining = 0
            continue

        if token in _CLAUSE_BREAKS:
            normalized.append(token)
            remaining = 0
            continue

        # "not only" and "not just" are emphasis, not negative polarity.
        if token == "not" and index + 1 < len(tokens) and tokens[index + 1] in {"only", "just"}:
            normalized.append(token)
            continue

        if token in _NEGATION_CUES:
            normalized.append("negation")
            remaining = max(remaining, scope)
            continue

        if remaining:
            normalized.append(f"negated_{token}")
            remaining -= 1
        else:
            normalized.append(token)

    return " ".join(normalized)
