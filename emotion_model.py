import joblib
from text_processing import normalize_negation

# If the model is uncertain, use the opposite class as a simple correction.
# Change this value to tune when the correction is applied.
LOW_CONFIDENCE_THRESHOLD = 50.0
EMOTION_OPPOSITES = {
    "joy": "sadness",
    "sadness": "joy",
    "fear": "anger",
    "anger": "fear",
    "love": "surprise",
    "surprise": "love",
}

# Load trained model and TF-IDF vectorizer
model = joblib.load("models/emotion_model.pkl")
vectorizer = joblib.load("models/tfidf_vectorizer.pkl")


def predict_emotion(text):
    text = normalize_negation(text)

    # Convert user text into TF-IDF features
    text_vector = vectorizer.transform([text])

    # Predict emotion
    emotion = str(model.predict(text_vector)[0])

    # Calculate confidence
    probabilities = model.predict_proba(text_vector)[0]
    confidence = float(max(probabilities) * 100)

    if confidence < LOW_CONFIDENCE_THRESHOLD:
        emotion = EMOTION_OPPOSITES.get(emotion, emotion)

    return emotion, confidence
