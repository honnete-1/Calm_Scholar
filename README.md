# Calm Scholar AI

A working Django + SQLite implementation of an academic companion for adult students.
Turn assignments into manageable steps, approve realistic study plans, check in at
your own pace, and use a quiet focus room. Inspired by the visual care in the supplied
RwandaWays reference; all interface code and illustrations here are original.

## Start on Windows

1. Extract the entire ZIP to a folder such as `D:\projects\calm-scholar`.
2. Install Python 3.11 or newer if needed. Enable **Add Python to PATH**.
3. Run `setup.bat`. It creates a virtual environment, installs dependencies, and
   creates the SQLite database. Internet access is needed for this first setup.
4. Run `start.bat` and open **http://127.0.0.1:8000**.
5. Create an account for an empty private workspace, or choose **Explore a demo**
   for fictional sample assignments in a separate guest workspace.

Keep the server window open while using the application. Stop it with Ctrl+C.
Your SQLite records persist when the server restarts. This is a local development
server, not a public deployment. No Node installation is required to run the app.

### Manual setup (Windows PowerShell)

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py runserver
```

Do not overwrite an existing `.env`; it may contain your settings and API key.

### macOS / Linux

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
cp .env.example .env
.venv/bin/python manage.py migrate
.venv/bin/python manage.py runserver
```

## Live AI

The project works without a key: planning, records, focus, and check-ins are real;
assistant replies and initial task breakdowns are clearly labeled scripted demo
responses. Sample guest workspaces always use demo AI, even with a key configured.

To enable live AI for registered accounts, edit `.env` locally:

```dotenv
OPENAI_API_KEY=your-own-key
OPENAI_MODEL=gpt-4.1-mini
```

Choose a chat-completions model available to your account and test its quality and
cost. Restart Django after changing the file. API usage requires its own billing.
Never share `.env` or paste keys into the web interface. The key remains server-side.
AI requests use a 25-second timeout, bounded output, JSON validation, and no SDK
retries. Provider failures fall back with an explicit notice. The provider may
retain API data according to its policies; `store=False` is not a blanket retention
guarantee. No model has been trained or fine-tuned for this implementation.

## Included features

- Landing page, registration, login, POST logout, and mobile workspace navigation.
- Assignment CRUD with courses, deadlines, priorities, and time estimates.
- AI or scripted task breakdown, editable steps, and progress tracking.
- Seven-day deadline-first planner with 25-minute sessions and 5-minute breaks.
- Gentle, balanced, and focused pacing; capacity and deadline conflict notices.
- Preview/confirm workflow: a proposed plan changes no sessions until approval.
- Recovery of unfinished work; completed sessions are deducted during replanning.
- Optional moods and private notes, without clinical scoring or diagnoses.
- Contextual companion, opt-in stored history, opt-in workload context, clear data flow.
- Focus timer with pause/reset and explicitly saved self-reported focus minutes.
- Search (Ctrl/Cmd+K), in-app deadline reminders, export, and deletion controls.
- Accessible labels, keyboard navigation, reduced motion, and responsive CSS.
- Original SVG artwork, bundled styles and JavaScript; no runtime CDN dependency.
- SQLite backup and expired-demo cleanup commands.

The frontend uses Django templates, custom design-token CSS, and small vanilla
JavaScript modules. The earlier Tailwind/HTMX suggestion was simplified to make
this runnable without a frontend toolchain or CDN. The included CSS is ready to
use and the backend remains Django + SQLite as requested.

## Planning rules

Times follow `TIME_ZONE` (Africa/Kigali by default). Declared daily availability is
capped at 60 minutes for Gentle, 240 for Balanced, and 360 for Focused. Sessions
stop at 22:00 and do not start in the past. Breaks consume capacity. The horizon
is seven days, so larger assignments may produce an explicit workload warning.
Overdue work is offered as catch-up today with a warning; a plan does not change
the official deadline. Completed future sessions remain intact, while unfinished
future sessions are replaced on confirmation. Missed past sessions remain for
history. The current MVP assumes the same availability every day and one time zone
per installation; it does not integrate university calendars.

Focus time is a separate self-reported metric. Saving it does not automatically
mark a study session complete. Use the completion control on the actual session.
Checking a subtask marks its sessions complete as an explicit user action.

## Privacy and support boundaries

Accounts scope API queries to the current user. CSRF protection applies to all
mutations. Passwords use Django hashing and validators. Stored conversation history
is off by default; enabling it allows history to be used in future AI requests.
Check-in notes are never used as AI workload context. Task breakdown necessarily
sends its title, description, and estimate when live AI is enabled.

The admin interface does not list conversations or check-in notes, although a
server/database administrator can access stored records. Avoid sensitive information
in demo workspaces. A static published preview uses fictional browser-local data
and scripted AI; it is not the Django server and has no real account authentication.

The assistant is not treatment or emergency care. The limited keyword safety
backstop is not a reliable clinical risk detector. Model instructions also address
urgent safety situations, but this does not establish clinical safety. Human review,
verified local support resources, and further scenario evaluation are necessary
before offering an emotional-support pilot to real students. No emergency
monitoring, automatic counselor messages, medical diagnosis, or phone deployment
is included.

## Tests

```bash
python -m pip install -r requirements-dev.txt
python -m pytest -q
python manage.py check
```

Tests cover account isolation, CSRF, signup, task editing, planning budgets,
deadlines, overlap, approval, opt-in context, provider failures, safety routing,
demo separation, export, and cascading deletion. Live provider quality and real
browser layout have not been verified in this build environment.

The delivered build passed 18 backend tests and the DOM workflow smoke test.
For the optional frontend DOM checks (Node required only for these tests):

```bash
python build_preview.py
npm install
npm test
```

`preview.html` is a static browser-local sample, not a substitute for running
Django. It can also be inspected as a visual preview; use fictional information.

## Hosting the actual Django application

Use a host that supports Python and a persistent disk for SQLite. Static website
hosting alone cannot run this backend. Keep a single application instance for this
small pilot; a shared multi-worker cache is needed before relying on request limits
across workers. Reassess SQLite if write concurrency grows.

Before hosting:

1. Set `DEBUG=false`, a strong `DJANGO_SECRET_KEY`, the actual `ALLOWED_HOSTS`, and
   matching `CSRF_TRUSTED_ORIGINS` in environment settings.
2. Put `DATABASE_PATH` on the persistent disk. Protect the database and backups
   using host permissions and encryption; they contain private student records.
3. Serve via a production WSGI server behind HTTPS, not `runserver`. If a trusted
   reverse proxy terminates HTTPS, configure Django's proxy settings for that host.
4. Run migrations, collect static files, and serve `/static/` from the web server.
5. Configure scheduled backups and `cleanup_demos`; verify a restoration process.
6. Add shared rate limiting, login abuse protection, request monitoring, operational
   error handling, and an AI spending cap before broad access.
7. Arrange student-support review and verified campus resources for a real pilot.

```bash
python manage.py migrate
python manage.py collectstatic --noinput
python manage.py check --deploy
gunicorn config.wsgi:application --workers 1 --bind 127.0.0.1:8000
python manage.py backup_db /secure/backups/calm-scholar-2026-10-10.sqlite3
python manage.py cleanup_demos
```

Backup creates a new consistent snapshot and refuses to overwrite a file. Use a
unique destination for each scheduled backup; do not put backups under web-served
static paths. To restore, stop the server, preserve the current database, and copy
a selected backup to `DATABASE_PATH`, then restart and verify your records.

## Structure

```
config/                  Django configuration and routing
scholar/models.py        SQLite-backed records
scholar/views.py         Account-scoped JSON actions
scholar/planner.py       Deterministic workload scheduler
scholar/ai.py            API integration, validation, explicit fallbacks
scholar/management/      Backup and demo maintenance
templates/               Landing, accounts, student workspace
static/                  Bundled CSS, JavaScript, SVG artwork
tests/                   Backend workflow tests
setup.bat / start.bat    Windows setup and launch
```

Future work: per-day availability, independently reviewed support flows,
calendar integration, task import, languages tested with local students, and
opt-in counselor booking. Institutional dashboards and clinical impact claims
are outside this implementation.
