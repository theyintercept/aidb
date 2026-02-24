# Deploying AIDB to Railway

## What you'll need
- A [Railway](https://railway.app) account (free to sign up)
- A [GitHub](https://github.com) account (free)
- Railway CLI installed (see Step 2)

---

## Step 1 — Create a GitHub repository

Railway deploys from GitHub. You need to push AIDB's code there first.

1. Go to [github.com/new](https://github.com/new)
2. Create a **private** repository called `aidb`
3. In your terminal, run:

```bash
cd /Users/bridgethorton/AIDB
git init
git add .
git commit -m "Initial AIDB deployment"
git remote add origin https://github.com/YOUR_USERNAME/aidb.git
git push -u origin main
```

> Note: `.gitignore` is already set up to exclude `.env`, the database, and uploaded files — these are kept off GitHub for security.

---

## Step 2 — Install the Railway CLI

```bash
brew install railway
```

Then log in:
```bash
railway login
```

---

## Step 3 — Create a Railway project

1. Go to [railway.app](https://railway.app) → **New Project**
2. Choose **Deploy from GitHub repo** → select your `aidb` repository
3. Railway will detect the `Procfile` and start building automatically

---

## Step 4 — Add a Volume (persistent database storage)

The database file must survive redeploys. Railway Volumes provide persistent disk storage.

1. In your Railway project dashboard, click **+ New** → **Volume**
2. Mount it at path: `/data`
3. Set the environment variable `DATABASE_PATH` to `/data/learning_sequence_v2.db`

---

## Step 5 — Upload your database to the Volume

**Option A: Built-in upload (recommended)**

1. Ensure the volume is attached to AIDB at `/data` (not Filebrowser).
2. Deploy AIDB, then visit:
   ```
   https://YOUR-AIDB-URL/admin/seed-database?key=YOUR_ADMIN_PASSWORD&format=html
   ```
3. Upload `learning_sequence_v2.db` using the form. Large files may take several minutes.

**Option B: Filebrowser** (if upload fails)

1. Deploy the Filebrowser template, set `USE_VOLUME_ROOT` = `1`
2. Detach volume from AIDB, attach to Filebrowser at `/data`
3. Upload via Filebrowser web UI, then detach and reattach to AIDB

---

## Step 6 — Set environment variables

In Railway dashboard → your project → **Variables**, add:

| Variable | Value |
|---|---|
| `SECRET_KEY` | A long random string (generate one below) |
| `ADMIN_USERNAME` | Your chosen admin username |
| `ADMIN_PASSWORD` | A strong password |
| `DATABASE_PATH` | `/data/learning_sequence_v2.db` |
| `AIDB_PUBLIC_URL` | Your Railway AIDB URL with HTTPS (e.g. `https://aidb-production-1b69.up.railway.app`) — ensures download URLs use HTTPS |
| `CORS_ORIGINS` | `https://theyintercept.com.au,https://www.theyintercept.com.au,https://tracker.theyintercept.com.au` |
| `FLASK_ENV` | `production` |

To generate a strong SECRET_KEY, run:
```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

---

## Step 7 — Add a custom domain (optional but recommended)

1. In Railway dashboard → **Settings** → **Domains**
2. Add `aidb.theyintercept.com.au`
3. In Hostinger DNS, add the CNAME record Railway gives you

---

## Step 8 — Verify deployment

Visit your Railway URL (e.g. `https://aidb-production.up.railway.app`) or your custom domain.

- `/api` → should return API info (public, no login needed)
- `/api/clusters?year=F` → should return Foundation clusters
- `/` → redirects to login (admin interface, protected)

---

## Updating AIDB after deployment

Whenever you make code changes:
```bash
cd /Users/bridgethorton/AIDB
git add .
git commit -m "Description of change"
git push
```
Railway automatically redeploys within ~30 seconds.

If you've added new data to the database on your Mac, repeat the Filebrowser upload steps above (Steps 5–10) to replace the database on the volume.

---

## API endpoints used by the main website and reporting tool

| Endpoint | Returns |
|---|---|
| `GET /api/clusters?year=F` | All Foundation clusters |
| `GET /api/cluster/<number>` | Single cluster with elements and resources |
| `GET /api/year-levels` | All year levels |
| `GET /api/resource/<id>/download` | Download a resource file |

These are public read-only endpoints — no API key needed.
