import os
from datetime import timedelta

import psycopg2
from psycopg2.extras import DictCursor
from flask import Flask, request, render_template, jsonify, session
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)

# Set these in Render Environment:
# SECRET_KEY = a long random secret
# DATABASE_URL = your Neon PostgreSQL connection string
app.secret_key = os.environ.get("SECRET_KEY", "change-this-local-development-key")
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=os.environ.get("COOKIE_SECURE", "true").lower() == "true",
    PERMANENT_SESSION_LIFETIME=timedelta(days=7),
)

DATABASE_URL = os.environ.get("DATABASE_URL")
BIRTHDAY_USERNAME = "aljawhara"

# Keep the existing club usernames. Passwords are set by each member on first login.
CLUB_MEMBERS = [
    ("rory", "Rory"),
    ("hanan", "Hanan"),
    ("amnah", "Amnah"),
    ("amal", "Amal"),
    ("aljawhara", "Aljawhara"),
    ("farah", "Farah"),
    ("lamya", "Lamya"),
    ("ola", "Ola"),
    ("malak", "Malak"),
    ("rawan", "Rawan"),
    ("anoud", "Anoud"),
    ("shahad", "Shahad"),
    ("raghad", "Raghad"),
    ("khuzama", "Khuzama"),
    ("nuha", "Nuha"),
    ("omar", "Omar"),
    ("nabil", "the count of monte cristo: Nabil"),
    ("mohammed", "Mohammed"),
    ("ateem", "Ateem"),
    ("rawabi", "Rawabi"),
    ("sarah", "Sara"),
    ("najah", "Najah"),
    ("ren", "Ren"),
    ("alia", "Alia"),
    ("afnan", "Afnan"),
]

def get_db_connection():
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL is not configured. Add your Neon connection string to the environment.")
    return psycopg2.connect(DATABASE_URL, sslmode="require", cursor_factory=DictCursor)

def init_db():
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,
                    username TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL DEFAULT 'PENDING',
                    name TEXT NOT NULL,
                    is_birthday_person BOOLEAN NOT NULL DEFAULT FALSE
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id SERIAL PRIMARY KEY,
                    from_user_id INTEGER NOT NULL REFERENCES users(id),
                    to_user_id INTEGER NOT NULL REFERENCES users(id),
                    message TEXT NOT NULL,
                    timestamp TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_messages_recipient_time
                ON messages (to_user_id, timestamp DESC)
            """)
            for username, name in CLUB_MEMBERS:
                cursor.execute("""
                    INSERT INTO users (username, password_hash, name, is_birthday_person)
                    VALUES (%s, 'PENDING', %s, %s)
                    ON CONFLICT (username) DO UPDATE
                    SET name = EXCLUDED.name,
                        is_birthday_person = EXCLUDED.is_birthday_person
                """, (username, name, username == BIRTHDAY_USERNAME))
        conn.commit()
    finally:
        conn.close()

@app.route("/")
def home():
    return render_template("page1.html")

@app.route("/login", methods=["POST"])
def login():
    data = request.get_json(silent=True) or {}
    username = str(data.get("username", "")).strip().lower()
    password = str(data.get("password", ""))

    if not username or not password:
        return jsonify({"error": "Please enter your username and password."}), 400
    if len(password) < 8:
        return jsonify({"error": "Your password must be at least 8 characters long."}), 400

    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT id, username, password_hash, name, is_birthday_person
                FROM users WHERE username = %s
            """, (username,))
            user = cursor.fetchone()

            if not user:
                return jsonify({"error": "This username is not registered as a club member."}), 401

            if user["password_hash"] == "PENDING":
                new_hash = generate_password_hash(password)
                cursor.execute("""
                    UPDATE users SET password_hash = %s
                    WHERE id = %s AND password_hash = 'PENDING'
                """, (new_hash, user["id"]))
                if cursor.rowcount != 1:
                    conn.rollback()
                    return jsonify({"error": "Please try signing in again."}), 409
                conn.commit()
            elif not check_password_hash(user["password_hash"], password):
                return jsonify({"error": "Incorrect password. Please try again."}), 401

            session.clear()
            session.permanent = True
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            session["name"] = user["name"]
            session["is_birthday_person"] = user["is_birthday_person"]

            return jsonify({
                "success": True,
                "name": user["name"],
                "is_birthday_person": user["is_birthday_person"],
                "message": "Welcome!"
            })
    finally:
        conn.close()

@app.route("/send-appreciation", methods=["POST"])
def send_appreciation():
    current_user_id = session.get("user_id")
    if not current_user_id:
        return jsonify({"error": "Please log in first."}), 401
    if session.get("is_birthday_person"):
        return jsonify({"error": "This account is for reading birthday messages."}), 403

    data = request.get_json(silent=True) or {}
    message = str(data.get("message", "")).strip()
    if not message:
        return jsonify({"error": "Please write a message first."}), 400
    if len(message) > 3000:
        return jsonify({"error": "Your message is too long (maximum 3000 characters)."}), 400

    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT id FROM users WHERE username = %s AND is_birthday_person = TRUE",
                           (BIRTHDAY_USERNAME,))
            birthday_user = cursor.fetchone()
            if not birthday_user:
                return jsonify({"error": "Birthday account is not configured."}), 500

            # Recipient is selected on the server, never accepted from the browser.
            cursor.execute("""
                INSERT INTO messages (from_user_id, to_user_id, message)
                VALUES (%s, %s, %s)
            """, (current_user_id, birthday_user["id"], message))
        conn.commit()
        return jsonify({"success": True, "message": "Your message has been sent to Aljawhara! 💝"})
    finally:
        conn.close()

@app.route("/inbox")
def inbox():
    if not session.get("user_id"):
        return jsonify({"error": "Please log in first."}), 401
    if not session.get("is_birthday_person"):
        return jsonify({"error": "The birthday inbox is private."}), 403

    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT sender.name AS from_name, m.message, m.timestamp
                FROM messages AS m
                JOIN users AS sender ON sender.id = m.from_user_id
                WHERE m.to_user_id = %s
                ORDER BY m.timestamp DESC, m.id DESC
            """, (session["user_id"],))
            rows = cursor.fetchall()
            return jsonify({
                "messages": [{
                    "from_name": row["from_name"],
                    "message": row["message"],
                    "timestamp": row["timestamp"].isoformat()
                } for row in rows]
            })
    finally:
        conn.close()

@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return jsonify({"success": True})

# Initialize tables and seed accounts when the app starts (including under Gunicorn).
with app.app_context():
    init_db()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5050)), debug=False)
