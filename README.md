# LearnTube: YouTube Coding Tutorial Learning Platform

LearnTube is a Python learning platform that catalogs coding tutorials from YouTube. It validates tutorial links, stores metadata and learner progress in SQLite, and provides notes, enrollment, search, and dashboard features. The design is intentionally modular so a web or mobile interface can be added without changing the domain services.

## Modules

1. Global tutorial catalog and YouTube embed-link extraction
2. User registration
3. Tutorial search by keyword and level
4. Enrollment and progress tracking
5. Learner notes and progress dashboard

## Run and test

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/pytest --cov=learning_platform --cov-report=term-missing
```

## Run the browser UI

```bash
.venv/bin/python app.py
```

Open <http://localhost:8000/catalog> in a browser. The global catalog supports searching tutorials, registering a learner, adding YouTube tutorials, and enrolling a learner. Data is stored in `learning_platform.db`.

On first start, the app seeds a demo learner (`demo@learntube.local`) and tutorials for AI, Python, NumPy, and pandas. Videos play inside the catalog and learner dashboard through YouTube iframes. Sign in with the demo account, open **My dashboard**, and use the progress and notes controls.

## Normal user workflow

1. Open **Global catalog** to browse or search all tutorials.
2. Register a new account or sign in with an existing account.
3. Select **Enroll and learn** on any catalog tutorial.
4. Open **My dashboard** to view only your enrollments.
5. Watch embedded videos, update progress, and save private notes.
6. Use **Global catalog** at any time; navigation does not log you out.
7. Select **Logout** when finished.

## Authentication

Dashboards and learner actions are private. Register with an email and a password of at least eight characters, or use the seeded demo account: `demo@learntube.local` / `demo-password`. Passwords are stored as PBKDF2-SHA256 hashes, and signed-in sessions use an HttpOnly cookie. A learner can only view and modify their own dashboard, progress, and notes. The catalog is public; enrollment requires login.

## Tests

The pytest suite covers YouTube URL validation, catalog persistence, enrollment, progress boundaries, notes, search, password authentication, and dashboard data. Run:

```bash
.venv/bin/pytest -q
```

The package can be used from Python:

```python
from learning_platform import LearningPlatform
from learning_platform.repository import SQLiteRepository

platform = LearningPlatform(SQLiteRepository("learning_platform.db"))
```
