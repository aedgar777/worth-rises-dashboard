# Worth Rises Telecom Rate Dashboard

Interactive dashboard for matching prison and jail telecom rates to jurisdictions, built for the Worth Rises Staff Technologist assignment.

---

## 1. Using the app

### Live site

Open **[https://worthrises.andrewedgar.io](https://worthrises.andrewedgar.io)** in your browser.

### Upload raw provider data

1. On the **Upload Data** panel, click **Choose File**.
2. Select the raw provider CSV. You can use the assignment test file included in this repo: **[sample-data/worth-rises-raw-data.csv](sample-data/worth-rises-raw-data.csv)** (download or clone the repo, then choose that file in the upload dialog).
3. Click **Upload & Generate**. The button shows a progress bar while the file uploads and the backend processes it. Allow 10-15 seconds for this to complete.

You only upload the **raw provider file**. The list of 163 jurisdictions to match against is built into the application (seeded from `backend/data/jurisdictions-to-match.csv` into Cloud SQL on deploy).

Each successful upload **replaces** any prior upload in the database so only the latest run is kept (demo storage policy).

**Expected raw CSV columns (Worth Rises test format):**


| Column          | Description                                                 |
| --------------- | ----------------------------------------------------------- |
| `provider`      | Telecom vendor (e.g. securus)                               |
| `state`         | 2-letter state code                                         |
| `county`        | County name (often blank in the test file)                  |
| `facility_id`   | Provider facility identifier                                |
| `facility_name` | Facility name as listed by the vendor                       |
| `phone`         | Facility phone number                                       |
| `in_state`      | `TRUE` / `FALSE` — whether the row is an in-state call rate |
| `per_min`       | Cost **per minute** in dollars (e.g. `0.085`)               |


The pipeline collapses paired in-state / out-of-state rows into one record per facility with `in_state_rate` and `out_of_state_rate`. A legacy wide-format CSV with `in_state_rate` and `out_of_state_rate` columns directly is also supported.

### Explore results

After processing, use the **Map** and **Tables** tabs.

**Map**

- Counties are colored by telecom rate (legend shows **$/min**).
- Toggle **In-state** vs **Out-of-state** rates.
- Click a county to see county and state rates in a popup; the selected county is outlined (fill color stays rate-based).
- Use **Search** to jump to a place via Google Places.

**Tables**

- **States** — all **matched** state jurisdictions with in-state and out-of-state rates.
- **Provider facilities** — every raw facility from your upload, with address and rates (table only; not in CSV downloads).
- **State dropdown** — pick a state to view matched **{State} counties** (empty states show “No county-level data for {State}”).

Unmatched and review-only rows are omitted from the web tables; use **Download unmatched list** to export them with reasons.

### Download results

The Tables view includes two downloads:

- **Download cleaned list** — matched jurisdictions only (same columns as the state and county tables): `type`, `jurisdiction`, `state`, `in_state_rate`, `out_of_state_rate`
- **Download unmatched list** — jurisdictions marked **review** or **unmatched**, with status, confidence, reference facility, and a combined reason field (`facility_rules` + `notes`)

Provider facilities with addresses and rates remain visible in the table; they are not included in either CSV.

---



## 2. Methodology

The goal is to produce **one row per target jurisdiction** (state prison system or county jail) with the best available **in-state** and **out-of-state** per-minute rates from messy vendor billing data.

### Inputs

1. **Jurisdictions reference** (built in, not uploaded) — 163 rows with:
  - `type`: `state` or `county`
  - `state`: 2-letter code
  - `county`: county name (empty for state rows)
2. **Raw provider CSV** — one or two rows per facility from the telecom vendor, with facility names and `per_min` rates.



### Step 1 — Normalize

- Column headers are normalized to a common schema.
- Worth Rises `per_min` + `in_state` boolean rows are merged: `TRUE` → in-state rate, `FALSE` → out-of-state rate.



### Step 2 — Classify each facility

Every raw facility record is labeled **include**, **exclude**, or **review** using keyword rules on `facility_name` (and `facility_type` when present). Rules live in `backend/app/transform/classifier.py` as regular expressions matched case-insensitively against the combined facility name and type.

**Excluded** (never matched) — examples from code:


| If the name contains…             | Rule label in code           |
| --------------------------------- | ---------------------------- |
| `juvenile`                        | juvenile facility            |
| `youth`                           | youth facility               |
| `federal`                         | federal facility             |
| `ice` or `immigration`            | ICE / immigration detention  |
| `work release`                    | work release program         |
| `halfway`                         | halfway house                |
| `probation` or `parole`           | probation / parole program   |
| `private` or `contract`           | private / contract facility  |
| `regional jail` or `multi-county` | regional / multi-county jail |


Example: **"Jefferson County Youth Detention Center"** matches `\byouth\b` and is excluded before scoring begins.

**Included** (preferred):

- **County targets:** `\bjail\b`, `\bsheriff`, `\bdetention center\b`, etc.
- **State targets:** `\bdepartment of corrections`, `\bdoc\b`, `\bpenitentiary\b`, etc.

**Review** (ambiguous type for the target):

- Jail-like names on a **state** jurisdiction (e.g. “Denver County Jail” vs Colorado state prison)
- Prison/DOC-like names on a **county** jurisdiction



### Step 3 — Match jurisdictions to facilities

For each of the 163 jurisdictions:

1. Consider raw records in the same **state**.
2. **Score** each candidate (0–1):
  - Start at 0.35 if not excluded
  - **+0.35** exact county field match, or **+0.25** if county name appears in facility name
  - **−0.20** county mismatch on county jurisdictions
  - **+0.15** if full state name appears in facility name (state jurisdictions)
  - **+0.20** DOC naming pattern (`DEPARTMENT`, `CORRECTION`) for state jurisdictions
  - **+0.15** if classification is `include`; **−0.05** if `review`
3. Keep candidates scoring **≥ 0.35**; pick the best if **≥ 0.45**.
4. **Status:**
  - **matched** — confidence ≥ 0.55
  - **review** — matched a facility but confidence is borderline
  - **unmatched** — no candidate above threshold (notes explain why; reference facility and `facility_rules` included in CSV)



### Step 4 — Resolve ties

When the top two candidates score within **0.05** of each other:

- If they share the **same** in-state and out-of-state rates → pick the higher text score (no Places call).
- If rates **differ** → use **Google Places** to geocode each facility and compare address alignment to the target county/state; the better-aligned facility wins.
- If rates differ but Places is unavailable → mark **review** with reduced confidence.



### Step 5 — Enrich and output

- **Google Places** fills missing counties in raw data, geocodes matched facilities for the map, and supplies formatted addresses in the provider facilities table.
- One wide-format row per jurisdiction is stored in PostgreSQL and returned to the frontend.



### Assumptions and limits

- State jurisdictions match to **DOC-level** facilities, not every individual prison.
- One primary facility is chosen per county.
- Rates are stored as **dollars per minute** from the raw file.
- Rules are keyword-based; production systems might add fuzzy matching or ML entity resolution.

Implementation: `backend/app/transform/classifier.py`, `matcher.py`, `columns.py`. Unit tests: `backend/tests/`.

---



## 3. Tech stack and infrastructure



### Repository layout


| Path                                      | Role                                                         |
| ----------------------------------------- | ------------------------------------------------------------ |
| `frontend/`                               | React + Vite + TypeScript UI (map, tables, upload)           |
| `backend/`                                | FastAPI service, matching pipeline, Cloud Run Dockerfile     |
| `backend/app/transform/`                  | CSV normalization, classification, jurisdiction matching     |
| `backend/app/places.py`                   | Google Places Text Search (geocoding, tie-breaks, addresses) |
| `backend/data/jurisdictions-to-match.csv` | Source of truth for the 163 jurisdictions                    |
| `backend/tests/`                          | Unit tests for classifier and matcher                        |
| `sample-data/worth-rises-raw-data.csv`    | Full assignment raw provider export for upload testing       |
| `infra/`                                  | SQL schema and deploy helpers                                |
| `docker-compose.yml`                      | Local PostgreSQL + API                                       |




### Tools and why I used them


| Tool                          | Where                                       | Why                                                    |
| ----------------------------- | ------------------------------------------- | ------------------------------------------------------ |
| **React + Vite + TypeScript** | `frontend/`                                 | Fast SPA build; type-safe UI for map and tables        |
| **@react-google-maps/api**    | `MapView.tsx`                               | County choropleth map, popups, Places search           |
| **FastAPI**                   | `backend/app/main.py`                       | Async CSV upload API, OpenAPI, Cloud Run friendly      |
| **pandas**                    | `backend/app/transform/`                    | CSV parsing, column normalization, row collapsing      |
| **SQLAlchemy**                | `backend/app/models.py`                     | ORM for uploads, matched rates, provider facilities    |
| **Google Places API**         | `backend/app/places.py`                     | Geocoding, county fill, tie-breaks, facility addresses |
| **PostgreSQL**                | Cloud SQL / Docker                          | Persistent uploads and results across sessions         |
| **Docker + Cloud Build**      | `backend/Dockerfile`, `frontend/Dockerfile` | Reproducible deploys to Cloud Run                      |
| **unittest**                  | `backend/tests/`                            | Regression tests for classify/match logic              |




### Cloud infrastructure (GCP)

Project: `**worth-rises-assignment**` · Region: `**us-central1**`

```
User browser  →  worthrises.andrewedgar.io
                        │
                        ▼
              Cloud Run: worth-rises-web
              (nginx + static React build)
                        │  HTTPS /api/*
                        ▼
              Cloud Run: worth-rises-api
              (FastAPI + matching pipeline)
                        │
          ┌─────────────┴─────────────┐
          ▼                           ▼
   Cloud SQL: worth-rises-db    Google Places API
   ├── worth_rises             (geocoding, addresses)
   │   ├── uploads
   │   ├── matched_rates
   │   └── provider_facilities
   └── worth_rises_jurisdictions
       └── jurisdictions (163 rows, seeded on startup)
```

**Data flow for one upload**

1. User selects raw CSV → frontend `POST /api/process` with multipart file.
2. API reads CSV into pandas, loads jurisdictions from Cloud SQL.
3. Pipeline: normalize → classify → score/match each jurisdiction → Places enrichment → save `matched_rates` and `provider_facilities`.
4. API returns `upload_id`; frontend fetches `/api/uploads/{id}/results`.
5. Map and tables render from JSON; CSV downloads are generated client-side (cleaned matched list and unmatched/review list).
6. **Demo behavior:** after a successful upload, previous upload rows are deleted from Cloud SQL so only the latest run remains. In a **production** environment, a single database would hold a curated master dataset: each new provider file would be matched against the same criteria, staged for human review, and only then merged into the authoritative rate table. The replace-on-upload pattern here is intentionally ephemeral to keep the demo simple and storage minimal.

