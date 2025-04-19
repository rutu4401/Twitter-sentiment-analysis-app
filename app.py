from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
from functools import wraps
from sentiment_model import predict_sentiment
from datetime import datetime
import os
import requests
import csv
from flask import get_flashed_messages
from checkfakenews import check_news

app = Flask(__name__)
app.secret_key = "your_secret_key"

UPLOAD_FOLDER = 'static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin123"

def get_db_connection():
    conn = sqlite3.connect("users.db", timeout=10) 
    conn.row_factory = sqlite3.Row
    return conn

with get_db_connection() as conn:
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL UNIQUE,
        email TEXT,
        password TEXT NOT NULL
    )
    """)
    try:
        cursor.execute("ALTER TABLE users ADD COLUMN is_admin INTEGER DEFAULT 0")
        conn.commit()
    except sqlite3.OperationalError:
        pass

    # ✅ Ensure news_posts table exists
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS news_posts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        news_text TEXT NOT NULL,
        image_file TEXT,
        prediction TEXT,
        confidence TEXT,
        timestamp TEXT,
        FOREIGN KEY(user_id) REFERENCES users(id)
    )
    """)
    conn.commit()
def get_all_tweets():
    tweets = []
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT posts.tweet, posts.image_filename, posts.sentiment, posts.flagged,
                   posts.timestamp, users.username
            FROM posts
            JOIN users ON posts.user_id = users.id
            ORDER BY posts.id DESC
        """)
        tweets_raw = cursor.fetchall()

        for row in tweets_raw:
            tweets.append({
                "tweet": row["tweet"],
                "image_filename": row["image_filename"],
                "sentiment": row["sentiment"],
                "flagged": row["flagged"],
                "username": row["username"],
                "timestamp": row["timestamp"]
            })
    return tweets


def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in first.')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return wrapper

def admin_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not session.get('is_admin'):
            flash('Admins only!')
            return redirect(url_for('home'))
        return f(*args, **kwargs)
    return wrapper

with get_db_connection() as conn:
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL UNIQUE,
        email TEXT,
        password TEXT NOT NULL,
        is_admin INTEGER DEFAULT 0
    )
    """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS posts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        tweet TEXT NOT NULL,
        image_filename TEXT,
        sentiment TEXT,
        flagged INTEGER DEFAULT 0,
        FOREIGN KEY(user_id) REFERENCES users(id)
    )
    """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS news_posts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        news_text TEXT NOT NULL,
        image_file TEXT,
        prediction TEXT,
        confidence TEXT,
        FOREIGN KEY(user_id) REFERENCES users(id)
    )
    """)
    conn.commit()


@app.route("/")
def home():
    return redirect(url_for("login"))

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        email = request.form["email"]
        password = request.form["password"]
        hashed_password = generate_password_hash(password)

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO users (username, email, password, is_admin) VALUES (?, ?, ?, 0)",
                       (username, email, hashed_password))
        conn.commit()
        conn.close()
        flash("Registered successfully. Please log in.")
        return redirect(url_for("login"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        # Check hardcoded admin credentials
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session["user_id"] = 0  # dummy id
            session["username"] = ADMIN_USERNAME
            session["is_admin"] = True
            flash("Admin login successful!", "success")
            return redirect(url_for("admin_options"))

        # Regular user login from DB
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
        user = cursor.fetchone()
        conn.close()

        if user and check_password_hash(user["password"], password):
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            session["is_admin"] = bool(user["is_admin"]) if "is_admin" in user.keys() else False
            flash("Login successful.")
            return redirect(url_for("predict"))
        else:
            flash("Invalid username or password.")

    return render_template("login.html")


@app.route("/admin_options")
def admin_options():
    if not session.get("is_admin"):
        flash("Unauthorized access", "danger")
        return redirect(url_for("login"))
    return render_template("admin_options.html")

@app.route("/predict", methods=["GET", "POST"])
def predict():
    if "user_id" not in session:
        flash("Please log in first.", "warning")
        return redirect(url_for("login"))

    sentiment = None

    if request.method == "POST":
        tweet = request.form["tweet"]
        sentiment, _ = predict_sentiment(tweet)

        def detect_fake_or_hate(tweet):
            hate_keywords = ["kill", "hate", "fake", "terrorist", "violence"]
            return any(word.lower() in tweet.lower() for word in hate_keywords)

        is_flagged = int(detect_fake_or_hate(tweet))

        try:
            file = request.files["image"]
        except KeyError:
            file = None

        filename = None
        if file and file.filename != "":
            filename = file.filename
            filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
            file.save(filepath)

        timestamp = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S')

        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO posts (user_id, tweet, image_filename, sentiment, flagged, timestamp)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (session["user_id"], tweet, filename, sentiment, is_flagged, timestamp))
            conn.commit()

        if sentiment == "Negative":
            flash("It seems you're going through something tough. You're not alone. 💙", "info")
        if is_flagged:
            flash("⚠️ This tweet may contain harmful or misleading content.", "danger")

        flash("Tweet and image uploaded!", "success")

    tweets = []
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT posts.tweet, posts.image_filename, posts.sentiment, posts.flagged,
                   posts.timestamp, users.username
            FROM posts
            JOIN users ON posts.user_id = users.id
            ORDER BY posts.id DESC
        """)
        tweets_raw = cursor.fetchall()

        for row in tweets_raw:
            tweets.append({
                "tweet": row["tweet"],
                "image_filename": row["image_filename"],
                "sentiment": row["sentiment"],
                "flagged": row["flagged"],
                "username": row["username"],
                "timestamp": row["timestamp"]  # ✅ Pass raw ISO format
            })

    return render_template("predict.html", sentiment=sentiment, tweets=tweets)




#@app.route("/tweet_feed")
#def tweet_feed():
 #   if "user_id" not in session and not session.get("admin"):
 #       flash("Please log in to view the feed.", "warning")
 #       return redirect(url_for("login"))

 #   conn = get_db_connection()
 #   cursor = conn.cursor()
 #   cursor.execute("""
 #       SELECT posts.id, posts.tweet, posts.image_filename, users.username, posts.sentiment, posts.flagged
 #       FROM posts
 #       JOIN users ON posts.user_id = users.id
 #       WHERE posts.sentiment IN ('Positive', 'Neutral') AND posts.flagged = 0
 #       ORDER BY posts.id DESC
 #   """)
 #   posts = cursor.fetchall()
 #   conn.close()

  #  return render_template("tweet_feed.html", posts=posts)
    

@app.route("/upload_and_post", methods=["POST"])
def upload_and_post():
    if "user_id" not in session:
        flash("Please log in first.", "warning")
        return redirect(url_for("login"))

    tweet = request.form["tweet"]
    file = request.files.get("image")

    filename = None
    if file and file.filename:
        filename = file.filename
        filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
        file.save(filepath)

    sentiment, _ = predict_sentiment(tweet)

    def detect_fake_or_hate(tweet):
        hate_keywords = ["kill", "hate", "fake", "terrorist", "violence"]
        for word in hate_keywords:
            if word.lower() in tweet.lower():
                return True
        return False 

    is_flagged = int(detect_fake_or_hate(tweet))

    if sentiment == "Negative":
        flash("It seems you're going through something tough. You're not alone. 💙", "info")
    if is_flagged:
        flash("⚠️ This tweet may contain harmful or misleading content.", "danger")

    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO posts (user_id, tweet, image_filename, sentiment, flagged)
            VALUES (?, ?, ?, ?, ?)
        """, (session["user_id"], tweet, filename, sentiment, is_flagged))
        conn.commit()

    flash("Tweet and image uploaded!", "success")
    return redirect(url_for("tweet_feed"))

@app.route("/check_news", methods=["GET", "POST"])
def check_news_route():
    if "user_id" not in session and not session.get("admin"):
        flash("Please log in first.", "warning")
        return redirect(url_for("login"))

    prediction = None
    confidence = None
    news_text = None
    filename = None

    if request.method == "POST":
        news_text = request.form.get("news_text")
        file = request.files.get("news_image")

        if file and file.filename:
            filename = file.filename
            filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
            file.save(filepath)

        url = "https://harismusa-claimcracker.hf.space/predict"
        headers = {"Content-Type": "application/json"}
        data = {"text": news_text}

        try:
            response = requests.post(url, json=data, headers=headers)
            if response.status_code == 200:
                result = response.json()
                prediction = result.get("prediction")
                confidence = result.get("confidence")
        except Exception as e:
            print("API call failed:", e)

        timestamp = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S')

        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO news_posts (user_id, news_text, image_file, prediction, confidence, timestamp)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (session["user_id"], news_text, filename, prediction, confidence, timestamp))
            conn.commit()

    news_items = []
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT news_posts.id, news_posts.news_text, news_posts.image_file, news_posts.prediction, news_posts.confidence, news_posts.timestamp, users.username
            FROM news_posts
            JOIN users ON news_posts.user_id = users.id
            ORDER BY news_posts.timestamp DESC
        """)


        raw_news = cursor.fetchall()

        for row in raw_news:
            news_items.append({
                "news_text": row["news_text"],
                "image_file": row["image_file"],
                "prediction": row["prediction"],
                "confidence": row["confidence"],
                "username": row["username"],
                "timestamp": row["timestamp"]
            })

    return render_template("news_feed.html", news_items=news_items)

@app.route("/check_tweet_sentiment", methods=["POST"])
@login_required
def check_tweet_sentiment():
    tweet = request.form.get("check_tweet")
    sentiment, _ = predict_sentiment(tweet)
    flash(f"The sentiment of the tweet is: {sentiment}", "info")
    return render_template("predict.html", sentiment_result=sentiment, tweets=get_all_tweets())


@app.route("/admin_panel")
def admin_panel():
    if not session.get("is_admin"):
        flash("Unauthorized access", "danger")
        return redirect(url_for("login"))

    conn = get_db_connection()
    cursor = conn.cursor()

    # Existing: Fetch tweets
    cursor.execute("""
        SELECT posts.id, posts.tweet, posts.image_filename, users.username
        FROM posts
        JOIN users ON posts.user_id = users.id
        ORDER BY posts.id DESC
    """)
    posts = cursor.fetchall()

    # ✅ New: Fetch news posts
    cursor.execute("""
        SELECT news_posts.id, news_posts.news_text, news_posts.image_file, news_posts.prediction,
               news_posts.confidence, users.username
        FROM news_posts
        JOIN users ON news_posts.user_id = users.id
        ORDER BY news_posts.id DESC
    """)
    news_posts = cursor.fetchall()

    conn.close()

    # ✅ Send both to template
    return render_template("admin_panel.html", posts=posts, news_posts=news_posts)


@app.route("/delete_post/<int:post_id>")
def delete_post(post_id):
    if not session.get("is_admin"):
        flash("Unauthorized", "danger")
        return redirect(url_for("login"))

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM posts WHERE id = ?", (post_id,))
    conn.commit()
    conn.close()

    flash("Post deleted!", "info")
    return redirect(url_for("admin_panel"))

@app.route("/delete_news_post/<int:post_id>", methods=["POST"])
@admin_required
def delete_news_post(post_id):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM news_posts WHERE id = ?", (post_id,))
        conn.commit()
    flash("News post deleted!", "info")
    return redirect(url_for("check_news_route"))



@app.route("/post_tweet", methods=["POST"])
@login_required
def post_tweet():
    flash("Post tweet logic placeholder – not yet implemented.")
    return redirect(url_for("predict"))

@app.route("/admin/dashboard")
@admin_required
def admin_dashboard():
    flash("Admin dashboard logic placeholder – not yet implemented.")
    return redirect(url_for("admin_panel"))

@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("login"))

def get_all_tweets():
    tweets = []
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT posts.tweet, posts.image_filename, posts.sentiment, posts.flagged,
                   posts.timestamp, users.username
            FROM posts
            JOIN users ON posts.user_id = users.id
            ORDER BY posts.id DESC
        """)
        tweets_raw = cursor.fetchall()

        for row in tweets_raw:
            tweets.append({
                "tweet": row["tweet"],
                "image_filename": row["image_filename"],
                "sentiment": row["sentiment"],
                "flagged": row["flagged"],
                "username": row["username"],
                "timestamp": row["timestamp"]
            })
    return tweets


if __name__ == "__main__":
    app.run(debug=True)
