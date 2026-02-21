# Recommendation: Rendering AIDB Data on the Website

**Purpose:** Start fresh—choose what from AIDB goes where on the website, using the website’s current layout as the target. Fit this with Hostinger hosting.

**Date:** February 2025

---

## 1. The Opportunity: Start Fresh

If the website had been built from scratch today, you would:

1. Use AIDB as the single source of truth
2. Call an API to get clusters, elements, and resources
3. Decide what to show where based on the data, not legacy IDs

You can still do this. The existing website shows how you want the information to look. The next step is to map that layout to AIDB data and build the integration.

---

## 2. Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        HOSTINGER                                  │
│                                                                   │
│  ┌─────────────────────┐         ┌─────────────────────────────┐  │
│  │  theyintercept.com.au │         │  api.theyintercept.com.au   │  │
│  │  (or subdomain)       │  ───►  │  (or /api path)             │  │
│  │                       │  fetch │                              │  │
│  │  • Static HTML/CSS/JS │         │  • Flask app (AIDB)         │  │
│  │  • scope-tracker      │         │  • JSON API endpoints       │  │
│  │  • Public-facing      │         │  • learning_sequence_v2.db  │  │
│  └─────────────────────┘         └─────────────────────────────┘  │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

**Two main options:**

| Option | Website | API | Pros | Cons |
|--------|---------|-----|------|------|
| **A: Same Hostinger account** | Static files (HTML/JS) | Flask app on subdomain or subfolder | One host, simpler | Need Python app setup |
| **B: Split** | Hostinger (static) | AIDB elsewhere (e.g. Railway, Render) | No Python on Hostinger | Two services, CORS setup |

**Recommendation:** Option A—host both on Hostinger. Use a subdomain (e.g. `api.theyintercept.com.au`) or a path (e.g. `theyintercept.com.au/api/`) for the API.

---

## 3. What the Website Needs from AIDB

From the current scope-tracker layout, the website likely needs:

| Data | Source in AIDB | API shape |
|------|----------------|-----------|
| Year levels (Foundation, Y1, Y2) | `year_levels` | List of {id, code, name} |
| Clusters per year | `clusters` + `cluster_elements` | List of {cluster_number, title, elements[]} |
| Elements in order | `cluster_elements` (sequence_order) | {element_number, title, …} |
| Resource links | `resources` (file_path or download URL) | Per element: list of {title, category, url} |
| Optional: load, stability, CPA | `elements` | Include in element payload |

**You choose what goes where.** The API exposes the data; the website decides what to render in each section.

---

## 4. API Endpoints to Add to AIDB

Add read-only JSON endpoints (no auth for public scope-tracker):

```
GET /api/year-levels          → List year levels
GET /api/clusters?year=F       → Clusters for Foundation (F, Y1, Y2)
GET /api/cluster/<cluster_number>/elements  → Elements + resources for a cluster
GET /api/resource/<id>/url     → Redirect or signed URL for file download
```

**Example response** (you can shape this to match the website):

```json
{
  "cluster_number": 101,
  "title": "Stable order & one to one correspondence",
  "year_level": "Foundation",
  "elements": [
    {
      "element_number": 10101,
      "title": "Stable order & one to one correspondence",
      "sequence_order": 1,
      "resources": [
        {"title": "Guided practice", "category": "Guided Practice", "url": "/api/resource/123/download"}
      ]
    }
  ]
}
```

---

## 5. How the Website Consumes the API

**Current:** Flat CSV / JSON files, possibly Google Drive links.

**New:** Fetch from AIDB API and render.

```javascript
// Example: fetch clusters for Foundation
const response = await fetch('https://api.theyintercept.com.au/api/clusters?year=F');
const clusters = await response.json();

// Render into your existing scope-tracker layout
clusters.forEach(cluster => {
  // You decide: which DOM elements, which sections, what order
  renderCluster(cluster);
});
```

You keep the same HTML structure and styling; only the data source changes.

---

## 6. Hostinger Setup

### 6.1 Option A: Both on Hostinger

**Website (static):**

- `public_html/` or `theyintercept.com.au` → HTML, CSS, JS
- No server-side code needed if you use client-side `fetch`

**API (Flask):**

- Subdomain: `api.theyintercept.com.au` → Python app (AIDB)
- Or path: `theyintercept.com.au/api/` → same app, under a path

**Steps:**

1. Create subdomain `api.theyintercept.com.au` in Hostinger
2. Point its document root to the AIDB app folder
3. Use Hostinger’s “Setup Python App” (or equivalent) for the Flask app
4. Follow `DEPLOY_HOSTINGER.md` for Flask deployment

### 6.2 CORS (if needed)

If the website and API use different origins (e.g. `www.theyintercept.com.au` and `api.theyintercept.com.au`), enable CORS in the Flask app:

```python
# In app.py, add:
from flask_cors import CORS
CORS(app, origins=["https://www.theyintercept.com.au", "https://theyintercept.com.au"])
```

### 6.3 File downloads

Resources (PDF, DOC, PPTX) can be:

- **Served by Flask:** e.g. `/api/resource/<id>/download` → stream file from DB or `uploads/`
- **Or moved to Hostinger storage:** upload files to a folder, store URLs in DB, and link directly (simpler for large files)

---

## 7. Moving AIDB to Your Website Computer

**Yes—moving the AIDB folder makes sense** for development:

1. Clone or copy the AIDB folder to the machine where the website lives
2. Run AIDB locally: `python app.py` → `http://localhost:8080`
3. Point the website’s `fetch` to `http://localhost:8080/api/...` during development
4. When ready, deploy AIDB to Hostinger and switch the base URL to the production API

**Folder structure suggestion:**

```
your-website-computer/
├── the-y-intercept-website/     # Existing site
│   └── scope-tracker/
└── AIDB/                        # Moved here
    ├── app.py
    ├── learning_sequence_v2.db
    ├── uploads/
    └── ...
```

Use a config in the website to switch between local and production API URLs.

---

## 8. Implementation Order

| Step | Task | Where |
|------|------|-------|
| 1 | Add `/api/` routes to AIDB (read-only, JSON) | AIDB `app.py` |
| 2 | Move AIDB folder to website computer | File system |
| 3 | Update website to fetch from `localhost:8080/api` | Website repo |
| 4 | Map API response to current scope-tracker layout | Website |
| 5 | Replace CSV/Drive links with API-driven links | Website |
| 6 | Deploy AIDB to Hostinger (subdomain or path) | Hostinger |
| 7 | Point website `fetch` to production API URL | Website |
| 8 | Deploy updated website to Hostinger | Hostinger |

---

## 9. Choosing What Goes Where

Because you’re starting fresh with the API:

1. **Inspect the current website** – Note each section (e.g. “Cluster list”, “Element list”, “Resource links”).
2. **Inspect the API responses** – See what AIDB returns for clusters, elements, resources.
3. **Map fields** – e.g. `cluster.title` → “Cluster name”, `element.resources[].url` → “Download link”.
4. **Ignore legacy IDs** – Use AIDB’s `cluster_number`, `element_number` as the canonical IDs. No need to preserve old simplified IDs.

The website becomes a view over AIDB. You choose what to show and where.

---

## 10. Summary

| Question | Answer |
|----------|--------|
| **Start from scratch?** | Yes. Use AIDB as the source; the website is a consumer. |
| **Move AIDB folder?** | Yes. Keep it next to the website for local development. |
| **Hostinger fit?** | Host both: static site + Flask API (subdomain or path). |
| **What to build first?** | API endpoints in AIDB, then website `fetch` + render. |
| **Legacy database/IDs?** | Not needed. Use AIDB IDs everywhere. |

---

## Appendix: API Endpoints (Implemented)

The following endpoints are now available in AIDB:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api` | GET | API info and endpoint list |
| `/api/year-levels` | GET | List year levels (F, Y1, Y2, …) |
| `/api/clusters?year=F` | GET | Clusters with elements and resources for a year |
| `/api/cluster/<cluster_number>` | GET | Single cluster detail by cluster_number |
| `/api/resource/<id>/download` | GET | Download a resource file (public) |

**Example:** `curl http://localhost:8080/api/clusters?year=F`
