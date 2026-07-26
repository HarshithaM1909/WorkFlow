# WorkFlow

**A full-stack employee management platform** — role-based access control, attendance and leave tracking, a live analytics dashboard, and a documented REST API, on a dark HTMX-driven UI backed by a real production PostgreSQL database.

![Django](https://img.shields.io/badge/Django-6.0-092E20?style=flat&logo=django&logoColor=white)
![DRF](https://img.shields.io/badge/Django%20REST%20Framework-red?style=flat&logo=django&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-Supabase-336791?style=flat&logo=postgresql&logoColor=white)
![HTMX](https://img.shields.io/badge/HTMX-3D72D7?style=flat&logo=htmx&logoColor=white)
![Python](https://img.shields.io/badge/Python-3.13-3776AB?style=flat&logo=python&logoColor=white)

**Live demo:** _coming soon_ · **API docs:** `/api/docs/` (Swagger UI)

---

## How it works

Two Django apps share one set of models — no logic duplicated between the web app and the API:

```
Browser (+ HTMX)  ──▶  emp/  views + templates  ──┐
                        (HTML, full or partial)    ├──▶  emp/models.py  ──▶  PostgreSQL
API client/Swagger ──▶  api/  DRF viewsets       ──┘     (single source     (Supabase)
                        (JSON)                             of truth)
```

- **`emp/`** owns the models, the server-rendered web app (function-based views + templates), and the permission rules. Business logic that has to stay correct in one place — like `LeaveRequest.approve()`'s guard against double-approval — lives on the model itself.
- **`api/`** is a DRF layer over the *same* models: serializers, viewsets, a router. It calls back into the model methods above instead of re-implementing them.
- Every write path (add employee, mark attendance, approve leave) is protected by a Django permission, checked the same way whether the request came from a browser or the API.
- The web UI never fully reloads for search, pagination, dashboard filtering, or leave approval — Django returns an HTML partial, and HTMX swaps it into the page (`hx-get`/`hx-post`/`hx-target`).

## Features

- **Role-based permissions** — CRUD/approve actions gated behind Django's permission framework, not just "logged in." Roles are a fixed set of IT job titles (Software Engineer, QA Engineer, DevOps Engineer, Team Lead, etc.), each with its own dashboard breakdown.
- **Admin-provisioned accounts, no public sign-up** — accounts are created via Django admin, not self-registration; see [Creating users](#creating-users) below.
- **Attendance tracking** — managers mark daily status (Present/Absent/Half Day/On Leave); employees view their own history.
- **Leave requests** — employees submit, managers approve/reject from a queue, with date validation and a guard against re-processing an already-decided request.
- **Analytics dashboard** — headcount by role and attendance trends (Chart.js), filterable by role and date range, refreshed live via HTMX.
- **REST API** (`/api/v1/`) — permission-scoped querysets, filtering, custom `approve`/`reject` actions, interactive Swagger docs at `/api/docs/`.
- **Testimonials & feedback** — public submission forms, moderated from the Django admin.

## Engineering highlights

- Reconciled Django migrations against a production database that had **drifted outside Django's control** — `SeparateDatabaseAndState` + idempotent SQL, verified to apply cleanly on both the live drifted DB and a fresh one built from scratch.
- Implemented **row-level scoping** that `DjangoModelPermissions` alone doesn't provide — `get_queryset()` overrides so an employee's `/api/v1/attendance/` only ever returns their own records.
- Kept approval logic in **one place** — `LeaveRequest.approve()`/`reject()` on the model, called from both the HTMX web view and the DRF action, so the two surfaces can't drift out of sync.
- Chose **HTMX over a SPA framework** for the UI — server-rendered partials, no client-side state management or separate JSON contract to maintain just for the frontend.
- Ran the full test suite against **real PostgreSQL**, not SQLite — catches constraint and migration behavior SQLite would silently miss.
- **Hardened for deployment** behind Render's reverse proxy — `SECURE_PROXY_SSL_HEADER`, HSTS/secure cookies gated on `DEBUG`, and a documented fix for Supabase's IPv6-only host being unreachable from some hosting networks.
- **No public self-registration** — internal HR tools in the real world don't let strangers create their own accounts and immediately see employee data; accounts here are provisioned via Django admin instead, matching how access is actually managed at most companies.

## Tech stack

**Backend:** Django 6, Django REST Framework, django-filter, drf-spectacular (OpenAPI/Swagger), django-htmx, django-crispy-forms + crispy-bootstrap5, psycopg2, dj-database-url, python-decouple, Pillow, gunicorn, whitenoise

**Frontend:** Bootstrap 5 (dark mode), Bootstrap Icons, HTMX, Chart.js, Google Fonts (Inter) — all via CDN

**Database & infra:** PostgreSQL (hosted on Supabase), Gmail SMTP, deployed on Render

## Testing

```
python manage.py test emp api
```

49 tests: model validation and state-transition guards, view permissions/redirects/rendering, HTMX partial responses, and API permission scoping/filtering/custom actions — run against a real PostgreSQL database created fresh for the test run.

## Setup

1. **Clone the repo and enter the project folder:**
   ```
   git clone <repo-url>
   cd Django-tut/myapp
   ```

2. **Install dependencies** (requires Python 3.13+):
   ```
   uv sync
   ```
   or, without `uv`:
   ```
   python -m venv .venv
   .venv\Scripts\activate   # Windows
   pip install Django dj-database-url python-decouple django-crispy-forms crispy-bootstrap5 psycopg2-binary Pillow gunicorn whitenoise djangorestframework django-filter drf-spectacular django-htmx
   ```

3. **Create a `.env` file** in this folder with:
   ```
   SECRET_KEY=your-django-secret-key
   DEBUG=True
   ALLOWED_HOSTS=127.0.0.1,localhost
   DB_PASSWORD=your-postgres-password
   EMAIL_HOST_USER=your-gmail-address
   EMAIL_HOST_PASSWORD=your-gmail-app-password
   ```

4. **Run migrations and start the server:**
   ```
   python manage.py migrate
   python manage.py createsuperuser
   python manage.py runserver
   ```

5. Visit `http://127.0.0.1:8000/` (redirects to login, then the employee list), `http://127.0.0.1:8000/admin/` for the admin panel, and `http://127.0.0.1:8000/api/docs/` for the API's interactive Swagger docs.

### Creating users

There's no public sign-up page — accounts are provisioned by an admin, not self-registered. To add someone:

1. Log into `/admin/` with a superuser account (created via `createsuperuser` above).
2. **Users → Add user**, set a username/password.
3. Optionally assign permissions directly, or add them to a **Group** with the relevant permissions (`add_emp`, `change_emp`, `delete_emp`, `view_dashboard`, `add_attendance`, `view_attendance`, `approve_leaverequest`).
4. If they're also an employee being tracked in the system, link the two: edit their `Emp` record and set its `user` field to the account you just created — that's what scopes their own attendance/leave views to just their data.

 
