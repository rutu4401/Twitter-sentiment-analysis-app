# 🐦 Twitter Sentiment Analysis Web App

This is a **Flask-based web application** that allows users to **analyze the sentiment of tweets** (Positive, Neutral, Negative) and also **detect fake or harmful content**. It features user login/registration, post sharing, and an admin dashboard to monitor content.

## 🔥 Features

- 📝 Tweet sentiment prediction (positive/negative/neutral)
- 🚨 Fake/Harmful news/content detection
- 👤 User login and registration
- 📰 Post tweets + images, like a mini Twitter
- 🛡️ Admin can view and delete inappropriate posts
- 🎨 Beautiful and interactive UI
- 📂 User posts stored in the database

---

## 🧠 Tech Stack

- **Frontend:** HTML, CSS, Bootstrap
- **Backend:** Python Flask
- **ML Models:** `.pkl` model for sentiment analysis & fake news detection
- **Database:** SQLite

---

## 🛠️ Installation Steps

1. **Clone the repository**
   ```bash
   git clone https://github.com/your-username/twitter-sentiment-analysis-app.git
   cd twitter-sentiment-analysis-app

2.Create and activate a virtual environment (optional but recommended)

python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

3,Install dependencies

pip install -r requirements.txt

4.Run the Flask app

python app.py

🚀 Project Structure

twitter-sentiment-analysis/
├── app.py
├── static/
│   ├── css/
│   └── images/
├── templates/
│   ├── index.html
│   ├── login.html
│   ├── register.html
│   ├── tweet_post.html
│   ├── result_tweet.html
│   ├── result_news.html
│   └── admin_dashboard.html
├── sentiment_model.pkl
├── fake_news_model.pkl
├── database.db
└── requirements.txt

🙋‍♀️ Developed By
Rutuja Gaikwad
