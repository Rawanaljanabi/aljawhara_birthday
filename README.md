# Aljawhara Birthday App

## Files
- `app.py`: Flask backend and database setup.
- `templates/page1.html`: website interface.
- `setup_db.py`: optional database initialization command.
- `requirements.txt`: Python dependencies.
- `static/bc.JPG`: add your existing birthday image here (same filename).

## Important security notes
- Do not reuse the old database URL/password that appeared in the previous `app.py`. Rotate that credential if it was real.
- Create a NEW Neon database for this birthday app.
- Set `DATABASE_URL` and `SECRET_KEY` as Render environment variables. Never commit them to GitHub.
- Passwords are stored as Werkzeug password hashes, not readable text.
- All members except `aljawhara` can send messages only. Only `aljawhara` can access `/inbox`.
- The server chooses the recipient; the browser cannot change it.

## Neon + Render setup
1. Create a new PostgreSQL project at https://neon.com/ and copy its connection string.
2. Create a separate GitHub repository for this birthday project. Do not overwrite the anniversary project.
3. Add `app.py`, `setup_db.py`, `requirements.txt`, `templates/page1.html`, and `static/bc.JPG`.
4. On Render, create a new **Web Service** connected to the new repository.
5. Set:
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `gunicorn app:app`
6. In Render Environment, add:
   - `DATABASE_URL` = Neon connection string
   - `SECRET_KEY` = a long random secret value
   - `COOKIE_SECURE` = `true`
7. Deploy. The app creates its tables and seeds the usernames at startup.

## First login
- Usernames are retained from the club app.
- Each member chooses their own password on their first login (minimum 8 characters).
- They must remember that password for future logins.
- `aljawhara` is the birthday inbox account.

## Note about free tiers
Free hosting/database plans have usage, sleep, storage, and policy limits that can change. Check the current plan limits before relying on the site for permanent storage. For a temporary birthday project, test the full login/send/inbox flow before sharing the link.
