# run_once_db_update.py

import sqlite3

conn = sqlite3.connect("users.db")
cursor = conn.cursor()

# Add columns if they don't already exist
try:
    cursor.execute("ALTER TABLE posts ADD COLUMN sentiment TEXT")
except:
    print("Column 'sentiment' already exists.")

try:
    cursor.execute("ALTER TABLE posts ADD COLUMN flagged INTEGER DEFAULT 0")
except:
    print("Column 'flagged' already exists.")

conn.commit()
conn.close()
