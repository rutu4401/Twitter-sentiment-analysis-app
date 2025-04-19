import requests
import csv
import os

# ❌ REMOVE THIS LINE:
# from checkfakenews import check_news

def check_news(news_text):
    url = "https://harismusa-claimcracker.hf.space/predict"
    headers = {"Content-Type": "application/json"}
    data = {"text": news_text}

    response = requests.post(url, json=data, headers=headers)
    if response.status_code == 200:
        result = response.json()
        prediction = result.get("prediction")
        confidence = result.get("confidence")
        save_result(news_text, prediction, confidence)
        return prediction, confidence
    else:
        return "Error", 0.0

def save_result(news_text, prediction, confidence, filename="TwitterSentiAnalysis/predictions.csv"):
    file_exists = os.path.isfile(filename)
    with open(filename, mode='a', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        if not file_exists:
            writer.writerow(['News Text', 'Prediction', 'Confidence'])
        writer.writerow([news_text, prediction, confidence])
