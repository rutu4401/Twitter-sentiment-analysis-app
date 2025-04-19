import os
import torch
import torch.nn.functional as F
from transformers import AutoModelForSequenceClassification, AutoTokenizer

# Disable OneDNN optimizations for TensorFlow (if needed)
os.environ["TF_ENABLE_ONEDNN_OPTS"] = "0"  

# Define model path
MODEL_PATH = r"C:\Users\Asus Laptop\Downloads\twitter_roberta_model\models--cardiffnlp--twitter-roberta-base-sentiment-latest\snapshots\4ba3d4463bd152c9e4abd892b50844f30c646708"

# Ensure the model path exists
if not os.path.exists(MODEL_PATH):
    raise FileNotFoundError(f"Model path '{MODEL_PATH}' does not exist. Please check the path.")

# Load fine-tuned model and tokenizer
tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH)
model = AutoModelForSequenceClassification.from_pretrained(MODEL_PATH)

# Sentiment labels
LABELS = ["Negative", "Neutral", "Positive"]

def predict_sentiment(text):
    """Tokenize input text and predict sentiment."""
    if not text.strip():
        return "Invalid input", None  # Handle empty input

    inputs = tokenizer(text, return_tensors="pt", padding=True, truncation=True, max_length=64)

    with torch.no_grad():
        outputs = model(**inputs)

    logits = outputs.logits
    probabilities = F.softmax(logits, dim=1).tolist()[0]  # Convert tensor to list
    sentiment = LABELS[torch.argmax(logits).item()]  # Get sentiment label

    return sentiment, probabilities
