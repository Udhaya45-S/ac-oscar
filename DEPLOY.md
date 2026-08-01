# Deploying Oscar Air Care

## What changed from the original code

- `app.secret_key`, admin username/passcode, and the MySQL password are now
  read from environment variables instead of being hardcoded. The app will
  refuse to start (`RuntimeError`) if `DB_PASSWORD` or `ADMIN_PASSCODE` are
  missing — this is intentional, so a misconfigured deploy fails loudly
  instead of running with a known/default password.
- `debug=True` is now driven by `FLASK_DEBUG` and defaults to `False`.
  Never set `FLASK_DEBUG=true` in production — Flask's debugger allows
  arbitrary code execution if someone reaches it.
- Raw exception messages are no longer sent to API clients (`str(e)`
  removed) — they're logged server-side instead, so internal errors
  (e.g. DB connection strings) don't leak to users.
- Added `gunicorn` + a `Procfile` so this can run as a real production
  WSGI server instead of Flask's dev server.
- Added `.env.example` / `.gitignore` / `python-dotenv` so secrets load
  from a local `.env` file in development and from the platform's env
  var settings in production.

## 1. Local test run

```bash
cd oscar-air-care
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# edit .env: set DB_PASSWORD, ADMIN_PASSCODE, FLASK_SECRET_KEY, etc.

python app.py
```

Visit http://localhost:5000

## 2. Deploying on Render (recommended, has managed MySQL-compatible option)

Render doesn't offer managed MySQL directly — easiest is to use a
managed MySQL add-on (e.g. PlanetScale, Aiven, or a Render Postgres
if you're open to switching — but this app uses MySQL syntax, so
stick with a MySQL-compatible host).

1. Push this project to a GitHub repo (`.env` is gitignored — don't commit it).
2. Create a MySQL database on **Aiven**, **PlanetScale**, or **Railway MySQL** — copy its host/port/user/password/db name.
3. On [render.com](https://render.com) → New → Web Service → connect your repo.
4. Build command: `pip install -r requirements.txt`
5. Start command: `gunicorn app:app`
6. Add environment variables in the Render dashboard:
   - `FLASK_SECRET_KEY` (generate with `python -c "import secrets; print(secrets.token_hex(32))"`)
   - `ADMIN_USERNAME`, `ADMIN_PASSCODE`
   - `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD`, `DB_NAME`
   - `FLASK_DEBUG=false`
7. Deploy. On first boot you need the table created — see step 8.
8. Run `python verify_db.py` once locally against the production DB
   (with prod env vars set) to create the database/table, or call
   `db.init_db()` via a one-off shell on the host.

## 3. Deploying on Railway (simplest — bundles MySQL + app together)

1. [railway.app](https://railway.app) → New Project → Deploy from GitHub repo.
2. Add a MySQL plugin/database from Railway's service catalog — it auto-generates `MYSQL_HOST`, `MYSQL_PORT`, `MYSQL_USER`, `MYSQL_PASSWORD`, `MYSQL_DATABASE` variables.
3. In your app service's variables, map those to what `db.py` expects
   (`DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD`, `DB_NAME`), or edit
   `db.py` to read Railway's variable names directly.
4. Add `FLASK_SECRET_KEY`, `ADMIN_USERNAME`, `ADMIN_PASSCODE`.
5. Set the start command to `gunicorn app:app` (Railway auto-detects `Procfile` too).
6. Deploy — Railway gives you a public URL immediately.

## 4. After first deploy

- Visit `/admin`, log in with your `ADMIN_USERNAME` / `ADMIN_PASSCODE`.
- Make a test booking on `/`, confirm it shows up in the admin table.
- Delete the test booking directly in the DB if needed.

## Still recommended (not done here, optional next steps)

- Hash the admin passcode (e.g. with `werkzeug.security.generate_password_hash`) instead of comparing plaintext, and consider rate-limiting `/api/admin/login`.
- Add HTTPS-only cookies (`SESSION_COOKIE_SECURE=True`) once served over HTTPS.
- Add basic input validation/length limits on booking fields server-side.
