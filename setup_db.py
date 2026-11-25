"""Initialize the birthday app's Neon PostgreSQL database and seed club accounts.

Run after setting DATABASE_URL:
    python setup_db.py

This is safe to run more than once. It does not overwrite existing password hashes.
"""
from app import init_db

if __name__ == "__main__":
    init_db()
    print("Birthday database is ready. Club accounts have been created.")
