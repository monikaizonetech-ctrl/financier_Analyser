# ProAnalyser — Full-Stack Financial Document Analysis Platform

A production-style clone of the ProAnalyser web app (dashboard, bank statement / GST / ITR
analysis, team management, and billing) built from the screenshots supplied in the project
requirements document.

**Stack:** React (Vite + Tailwind) · FastAPI · SQLAlchemy · PostgreSQL · JWT Auth

---

## 1. Project Architecture

### Frontend (`/frontend`)
React SPA built with Vite. Talks to the backend exclusively over REST via Axios, with a JWT
bearer token attached to every request. Routes are guarded by `ProtectedRoute`, which also
restricts `/team-management` to Admin/Manager roles.

```
frontend/src/
├── api/axios.js          # Axios instance + auth interceptor
├── context/               # AuthContext (session), NotificationContext (toasts)
├── routes/ProtectedRoute.jsx
├── layouts/DashboardLayout.jsx   # Sidebar + Header shell
├── components/            # Sidebar, Header, DataTable, Pagination, Modal, Badge, etc.
└── pages/                 # Login, Register, Dashboard, MyReports, TeamReports,
                            # TeamManagement, Billing, Help, UploadReport
```

### Backend (`/backend`)
FastAPI app, layered as:

```
backend/app/
├── main.py           # App factory, CORS, router registration
├── database.py       # SQLAlchemy engine/session
├── core/              # settings (env config) + security (JWT/bcrypt)
├── dependencies/       # get_current_user / require_roles guards
├── models/             # SQLAlchemy ORM models
├── schemas/            # Pydantic request/response models
├── routers/            # auth, dashboard, reports, team, billing, support
└── services/           # file_analysis_service (parsing + Excel/PDF generation)
```

### Database
PostgreSQL, 6 tables: `users`, `reports`, `report_files`, `subscriptions`, `transactions`
(schema also in `database/schema.sql`). Tables are auto-created by SQLAlchemy on backend
startup (`Base.metadata.create_all`); for real production use, switch to Alembic migrations.

**Relationships:**
- `users.added_by_id` → self-referencing FK. The Admin who created the workspace is the
  "organization owner"; every user they add via Team Management shares that `org_id`. This
  is what scopes **Team Reports** and **Team Management** to the right group of people.
- `reports.owner_id` → `users.id` (one user has many reports)
- `report_files.report_id` → `reports.id` (one report has many uploaded files)
- `subscriptions.user_id` → `users.id` (1:1 — each user has one billing subscription)
- `transactions.user_id` → `users.id` (1:many — billing history)

### Authentication & Authorization flow
1. `POST /auth/register` creates a new user as **Admin** of a brand-new workspace + a Free
   Trial subscription, and returns a JWT.
2. `POST /auth/login` verifies bcrypt-hashed password, returns a JWT (24h expiry by default).
3. Every protected endpoint depends on `get_current_user`, which decodes the JWT and loads
   the user from Postgres.
4. Role-gated endpoints (adding/removing team members) use `require_roles(Admin, Manager)`.
5. Frontend stores the JWT in `localStorage` and auto-attaches it via an Axios interceptor;
   a 401 response clears the session and redirects to `/login`.

### Report analysis flow (matches the screenshots)
1. **Dashboard** → click **New Report** → modal collects Report Name, optional Reference ID,
   and Report Type (Bank Statement / GST / ITR) → `POST /reports`.
2. Redirects to the **Upload** screen (`/upload-report/:id`, mirrors the "ITR DEMO" screenshot)
   → `POST /reports/{id}/files` for each uploaded file (stored under `backend/uploads/{report_id}/`).
3. Click **Analyse** → `POST /reports/{id}/analyse`. For CSV/XLSX bank statements this actually
   parses the rows with pandas and computes total credits/debits/closing balance. For PDF-only
   GST/ITR documents (which would need a licensed OCR/GST-API integration to parse in real life)
   it produces a clearly-labelled metadata summary so the workflow stays fully functional. This
   also decrements subscription credits.
4. Report status flips to **Ready to use** → **My Reports** / **Team Reports** show a download
   modal that streams a generated Excel (`openpyxl`) or PDF (`reportlab`) report on demand.

---

## 2. Setup Instructions

### Prerequisites
- Node.js 18+
- Python 3.11+
- PostgreSQL 14+ (or use the provided Docker Compose)

### Option A — Docker Compose (recommended)
```bash
docker compose up --build
```
This starts Postgres on `5432`, the API on `8000`, and the frontend dev server on `5173`.
Then seed the database (see step 5 below) by running it inside the backend container:
```bash
docker compose exec backend python seed_db.py
```

### Option B — Run manually

**1. PostgreSQL**
```bash
createdb financier_db
createuser proanalyser_user --pwprompt   # set password to proanalyser_pass, or update .env
```

**2. Backend**
```bash
cd backend
python -m venv venv && source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env        # edit DATABASE_URL / JWT_SECRET_KEY as needed

```
API now runs at `http://localhost:8000` (interactive docs at `/docs`).

**3. Seed sample data**
```bash
python seed_db.py
```

**4. Frontend**
```bash
cd frontend
npm install
cp .env.example .env        # points VITE_API_BASE_URL at the backend
npm run dev
```
App runs at `http://localhost:5173`.

**5. Test login credentials** (created by `seed_db.py`)
| Role    | Email                         | Password     |
|---------|--------------------------------|--------------|
| Admin   | monika@proanalyser.in          | Admin@123    |
| Manager | ravi.manager@proanalyser.in    | Manager@123  |
| Member  | ananya.member@proanalyser.in   | Member@123   |

You can also register a brand-new workspace from the **Create one** link on the login page —
the first user of a workspace is always its Admin.

---

## 3. API Endpoints

All endpoints are prefixed with `/api/v1`. Full interactive documentation (OpenAPI/Swagger) is
served automatically by FastAPI at `http://localhost:8000/docs`.

| Method | Endpoint                             | Description                              |
|--------|----------------------------------------|-------------------------------------------|
| POST   | `/auth/register`                       | Create workspace + Admin user             |
| POST   | `/auth/login`                          | Login, returns JWT                        |
| GET    | `/auth/me`                             | Current user profile                      |
| GET    | `/dashboard`                           | KPI stats + subscription summary          |
| POST   | `/reports`                             | Create a new report                       |
| GET    | `/reports`                             | List my reports (search, pagination)      |
| GET    | `/reports/team`                        | List team reports (search by email/name)  |
| GET    | `/reports/{id}`                        | Report detail incl. files                 |
| POST   | `/reports/{id}/files`                  | Upload a source file                      |
| DELETE | `/reports/{id}/files/{file_id}`        | Remove an uploaded file                   |
| POST   | `/reports/{id}/analyse`                | Run analysis, consume credits             |
| GET    | `/reports/{id}/download?file_format=`  | Download result as `xlsx` or `pdf`        |
| DELETE | `/reports/{id}`                        | Delete a report                           |
| GET    | `/team/users`                          | List team members (filter by role)        |
| POST   | `/team/users`                          | Add a team member (Admin/Manager)         |
| PUT    | `/team/users/{id}`                     | Update role/status (Admin/Manager)        |
| DELETE | `/team/users/{id}`                     | Remove a team member (Admin)              |
| GET    | `/billing`                             | Subscription + transaction history        |
| POST   | `/billing/avail-paid-trial`            | Activate paid trial                       |
| POST   | `/billing/upgrade?plan=`               | Upgrade plan (Standard/Pro/Enterprise)    |
| GET    | `/support/contact`                     | Support contact info                      |
| POST   | `/support/requests`                    | Raise a support request                   |

---

## 4. Notes & Known Limitations

- **File parsing depth**: real structured parsing (pandas) is implemented for CSV/XLSX bank
  statements. GST/ITR PDFs and scanned bank statements get a metadata-based summary rather than
  full OCR extraction, since that requires a licensed OCR/GST-API/ITR-parsing provider not
  specified in the source document — the analysis pipeline (`app/services/file_analysis_service.py`)
  is structured so swapping in a real parser later is a one-function change.
- **Migrations**: tables are created via `Base.metadata.create_all` for simplicity. For schema
  evolution in production, initialize Alembic (`alembic init`) against these models.
- **Payments**: `/billing/upgrade` and `/billing/avail-paid-trial` update subscription state and
  log a transaction, but do not integrate a real payment gateway (Razorpay/Stripe) — wire one in
  before charging real users.
- **File storage**: uploaded files are stored on local disk under `backend/uploads/`. For a
  multi-instance deployment, point `UPLOAD_DIR` at a shared volume or swap in S3-compatible
  storage.
