"""Train and evaluate the emotion classifier using the installed local dataset."""
from __future__ import annotations

import json
import os

import joblib
import pyarrow.parquet as parquet
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import SGDClassifier
from sklearn.metrics import accuracy_score, classification_report
from sklearn.model_selection import train_test_split

from text_processing import normalize_negation


PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
DATASET_PATH = os.path.join(PROJECT_DIR, "dataset_loader.py")
MODEL_DIR = os.path.join(PROJECT_DIR, "models")

def load_local_dataset():
    if not os.path.isfile(DATASET_PATH):
        raise FileNotFoundError(f"Local Parquet dataset not found: {DATASET_PATH}")

    table = parquet.read_table(DATASET_PATH, columns=["text", "label"])
    metadata = parquet.ParquetFile(DATASET_PATH).metadata.metadata or {}
    huggingface_metadata = metadata.get(b"huggingface")
    if not huggingface_metadata:
        raise ValueError("Dataset is missing its Hugging Face label metadata.")

    features = json.loads(huggingface_metadata.decode("utf-8"))["info"]["features"]
    label_names = features["label"]["names"]
    texts = [str(text or "") for text in table.column("text").to_pylist()]
    label_ids = [int(label) for label in table.column("label").to_pylist()]
    if not texts or len(texts) != len(label_ids):
        raise ValueError("Dataset has no rows or mismatched text and label columns.")
    if any(label < 0 or label >= len(label_names) for label in label_ids):
        raise ValueError("Dataset contains a label id missing from its label metadata.")
    return texts, [label_names[label] for label in label_ids], label_names


def main():
    print("Loading installed local Parquet dataset:", DATASET_PATH)
    texts, labels, label_names = load_local_dataset()
    print(f"Loaded {len(texts):,} examples")
    print("Labels:", ", ".join(label_names))

    train_texts, test_texts, y_train, y_test = train_test_split(
        texts,
        labels,
        test_size=0.2,
        random_state=42,
        stratify=labels,
    )
    print(f"Train examples: {len(train_texts):,}; test examples: {len(test_texts):,}")

    print("Applying shared negation normalization...")
    normalized_train = [normalize_negation(text) for text in train_texts]
    normalized_test = [normalize_negation(text) for text in test_texts]

    vectorizer = TfidfVectorizer(
        lowercase=True,
        stop_words="english",
        max_features=20000,
        ngram_range=(1, 2),
    )
    X_train = vectorizer.fit_transform(normalized_train)
    X_test = vectorizer.transform(normalized_test)

    print("Training classifier...")
    model = SGDClassifier(
        loss="log_loss",
        random_state=42,
        max_iter=1000,
        tol=1e-3,
    )
    model.fit(X_train, y_train)

    predictions = model.predict(X_test)
    accuracy = accuracy_score(y_test, predictions)
    print(f"\nHoldout accuracy: {accuracy * 100:.2f}%")
    print("\nClassification report:")
    print(classification_report(y_test, predictions, labels=label_names, zero_division=0))

    # The shared normalizer maps all supported negation forms to this marker,
    # including apostrophe, unpunctuated, and split contractions.
    negation_mask = ["negation" in text.split() for text in normalized_test]
    negation_truth = [label for label, is_negated in zip(y_test, negation_mask) if is_negated]
    negation_predictions = [pred for pred, is_negated in zip(predictions, negation_mask) if is_negated]
    if negation_truth:
        print(
            f"Negation subset accuracy ({len(negation_truth):,} examples): "
            f"{accuracy_score(negation_truth, negation_predictions) * 100:.2f}%"
        )
    else:
        print("No negation-bearing examples were found in the holdout set.")

    os.makedirs(MODEL_DIR, exist_ok=True)
    joblib.dump(model, os.path.join(MODEL_DIR, "emotion_model.pkl"))
    joblib.dump(vectorizer, os.path.join(MODEL_DIR, "tfidf_vectorizer.pkl"))
    joblib.dump(label_names, os.path.join(MODEL_DIR, "label_names.pkl"))
    print("Saved model, vectorizer, and labels to:", MODEL_DIR)


if __name__ == "__main__":
    main()
