"""LearnTube web application with catalogue and learner dashboards."""

import html
import secrets
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse
from http.cookies import SimpleCookie

sys.path.insert(0, str(Path(__file__).parent / "src"))

from learning_platform import LearningPlatform
from learning_platform.repository import SQLiteRepository


repository = SQLiteRepository("learning_platform.db")
platform = LearningPlatform(repository)
sessions: dict[str, int] = {}


def seed_demo_data() -> None:
    """Create repeatable demo data without duplicating existing records."""
    user_row = repository.fetchone("SELECT id FROM users WHERE email = ?", ("demo@learntube.local",))
    if user_row is None:
        demo_user_id = platform.add_user("Demo Learner", "demo@learntube.local", "demo-password").id
    else:
        demo_user_id = user_row["id"]
        if not repository.fetchone("SELECT password_hash FROM users WHERE id = ? AND password_hash != ''", (demo_user_id,)):
            repository.execute(
                "UPDATE users SET password_hash = ? WHERE id = ?",
                (platform._hash_password("demo-password"), demo_user_id),
            )
    samples = [
        ("Artificial Intelligence Fundamentals", "Learn the foundations of AI, machine learning, and neural networks.",
         "https://www.youtube.com/watch?v=aircAruvnKk", "AI", "Beginner"),
        ("Python Programming for Beginners", "Build a strong foundation in Python syntax and problem solving.",
         "https://www.youtube.com/watch?v=_uQrJ0TkZlc", "Python", "Beginner"),
        ("NumPy for Data Science", "Work with arrays, vectorized operations, and numerical computing.",
         "https://www.youtube.com/watch?v=QUT1VHiLmmI", "NumPy", "Intermediate"),
        ("Python Data Analysis with Pandas", "Clean, transform, and explore datasets with pandas.",
         "https://www.youtube.com/watch?v=vmEHCJofslg", "Python", "Intermediate"),
    ]
    for title, description, url, topic, level in samples:
        if repository.fetchone("SELECT id FROM tutorials WHERE title = ?", (title,)) is None:
            platform.add_tutorial(title, description, url, topic, level)
    sample_titles = [sample[0] for sample in samples[:3]]
    sample_rows = repository.fetchall(
        f"SELECT id FROM tutorials WHERE title IN ({','.join('?' for _ in sample_titles)})",
        sample_titles,
    )
    if not repository.fetchone(
        "SELECT id FROM enrollments WHERE user_id = ? AND tutorial_id = ?",
        (demo_user_id, sample_rows[0]["id"]),
    ):
        repository.execute("DELETE FROM enrollments WHERE user_id = ?", (demo_user_id,))
    for row in sample_rows:
        existing = repository.fetchone(
            "SELECT id FROM enrollments WHERE user_id = ? AND tutorial_id = ?",
            (demo_user_id, row["id"]),
        )
        if existing is None:
            platform.enroll(demo_user_id, row["id"])


def esc(value: object) -> str:
    return html.escape(str(value))


def page(body: str, message: str = "", user_id: int | None = None) -> str:
    notice = f'<div class="notice">{esc(message)}</div>' if message else ""
    auth_nav = (
        f'<a href="/dashboard/{user_id}">My dashboard</a><a href="/logout">Logout</a>'
        if user_id is not None else '<a href="/login">Login</a>'
    )
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport"
content="width=device-width, initial-scale=1"><title>LearnTube</title>
<style>
* {{ box-sizing:border-box }} body {{ margin:0; font-family:Arial,sans-serif; background:#f4f6f8; color:#111 }}
header {{ background:#121826; color:white; padding:24px max(24px,calc((100% - 1180px)/2)) }}
header h1 {{ margin:0 0 6px }} header p {{ margin:0 0 18px; color:#d5dbea }}
nav a {{ color:white; margin-right:20px; text-decoration:none; font-weight:bold }}
main {{ max-width:1180px; margin:28px auto; padding:0 24px }} h2 {{ margin-top:0 }}
.grid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(320px,1fr)); gap:20px }}
.card, form, .hero {{ background:white; border:1px solid #d5d9dd; border-radius:10px; padding:20px; box-shadow:0 2px 6px #0000000b }}
.card h3 {{ margin:0 0 8px }} label {{ display:block; margin-top:11px; font-weight:bold }}
input, textarea, select {{ width:100%; padding:10px; margin-top:5px; border:1px solid #aeb5bd; border-radius:5px; font:inherit }}
textarea {{ min-height:90px }} button, .button {{ display:inline-block; margin-top:14px; padding:10px 15px; background:#121826; color:white; border:0; border-radius:5px; cursor:pointer; text-decoration:none }}
.notice {{ background:#e4f2e5; border:1px solid #8bb78f; padding:12px; margin-bottom:18px; border-radius:5px }}
.muted {{ color:#59636e }} .meta {{ color:#59636e; font-size:.92rem }} .stats {{ display:flex; gap:14px; flex-wrap:wrap; margin:18px 0 }}
.stat {{ background:#e8edf5; border-radius:8px; padding:14px 18px }} .stat b {{ display:block; font-size:1.5rem }}
.video {{ width:100%; aspect-ratio:16/9; border:0; border-radius:7px; margin:12px 0 }}
.progress {{ height:10px; background:#dfe3e8; border-radius:5px; margin:10px 0 }} .progress span {{ display:block; height:100%; background:#3a67a8; border-radius:5px }}
.actions {{ display:flex; gap:9px; flex-wrap:wrap; align-items:end }} .actions form {{ box-shadow:none; padding:0; border:0; flex:1; min-width:150px }}
</style></head><body><header><h1>LearnTube</h1>
<p>Learn from curated coding videos, track progress, and keep your notes.</p>
<nav><a href="/catalog">Global catalog</a><a href="/add">Add tutorial</a><a href="/register">Register</a>{auth_nav}</nav>
</header><main>{notice}{body}</main></body></html>"""


def value(values: dict, key: str) -> str:
    return values.get(key, [""])[0].strip()


def user_name(user_id: int) -> str:
    row = repository.fetchone("SELECT name FROM users WHERE id = ?", (user_id,))
    if row is None:
        raise ValueError("Learner not found")
    return row["name"]


class Handler(BaseHTTPRequestHandler):
    def current_user_id(self) -> int | None:
        cookie = SimpleCookie(self.headers.get("Cookie", ""))
        token = cookie.get("session")
        return sessions.get(token.value) if token else None

    def require_user(self) -> int | None:
        user_id = self.current_user_id()
        if user_id is None:
            self.send_html(page('<h2>Login required</h2><p>Please sign in to access your private dashboard.</p>'
                                '<a class="button" href="/login">Sign in</a>'), 401)
        return user_id

    def send_html(self, content: str, status: int = 200, headers: dict | None = None) -> None:
        encoded = content.encode()
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        for key, header_value in (headers or {}).items():
            self.send_header(key, header_value)
        self.end_headers()
        self.wfile.write(encoded)

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        query = parse_qs(parsed.query)
        try:
            if parsed.path in {"/", "/catalog"}:
                keyword, level = value(query, "q"), value(query, "level")
                tutorials = platform.search_tutorials(keyword, level or None)
                cards = "".join(
                    f"""<article class="card"><h3>{esc(t.title)}</h3>
                    <p class="meta">{esc(t.topic)} · {esc(t.level)}</p>
                    <p>{esc(t.description)}</p><iframe class="video" src="{esc(t.youtube_url)}"
                    title="{esc(t.title)}" allowfullscreen loading="lazy"></iframe>
                    <form method="post" action="/enroll"><input type="hidden" name="tutorial_id" value="{t.id}">
                    <button>Enroll and learn</button></form></article>""" for t in tutorials
                ) or '<p class="muted">No tutorials found.</p>'
                body = f"""<section class="hero"><h2>Find your next lesson</h2>
                <form method="get" action="/catalog"><label>Search by topic or keyword</label>
                <input name="q" value="{esc(keyword)}" placeholder="AI, Python, NumPy...">
                <label>Level</label><select name="level"><option value="">All levels</option>
                {''.join(f'<option value="{x}" {"selected" if level == x else ""}>{x}</option>' for x in ["Beginner", "Intermediate", "Advanced"])}
                </select><button>Search catalogue</button></form></section><br>
                <h2>{len(tutorials)} tutorials available</h2><section class="grid">{cards}</section>"""
                self.send_html(page(body, user_id=self.current_user_id()))
            elif parsed.path.startswith("/dashboard/"):
                user_id = int(parsed.path.rsplit("/", 1)[1])
                signed_in = self.require_user()
                if signed_in is None:
                    return
                if signed_in != user_id:
                    self.send_html(page("<h2>Forbidden</h2><p>You cannot access another learner's dashboard.</p>"), 403)
                    return
                name = user_name(user_id)
                rows = platform.dashboard_details(user_id)
                cards = "".join(f"""<article class="card"><h3>{esc(r["title"])}</h3>
                <p class="meta">{esc(r["topic"])} · {r["progress"]}% complete</p>
                <iframe class="video" src="{esc(r["youtube_url"])}" title="{esc(r["title"])}" allowfullscreen></iframe>
                <div class="progress"><span style="width:{r["progress"]}%"></span></div>
                <form method="post" action="/progress"><input type="hidden" name="user_id" value="{user_id}">
                <input type="hidden" name="tutorial_id" value="{r["tutorial_id"]}"><label>Update progress (%)</label>
                <input name="progress" type="number" min="0" max="100" value="{r["progress"]}" required><button>Save progress</button></form>
                <form method="post" action="/note"><input type="hidden" name="user_id" value="{user_id}">
                <input type="hidden" name="tutorial_id" value="{r["tutorial_id"]}"><label>Learning note</label>
                <textarea name="body" placeholder="What did you learn?"></textarea><button>Save note</button></form>
                {f'<p><b>Latest note:</b> {esc(r["note"])}</p>' if r["note"] else ''}</article>""" for r in rows)
                total = len(rows)
                average = round(sum(r["progress"] for r in rows) / total) if total else 0
                self.send_html(page(f"""<section class="hero"><h2>{esc(name)}'s dashboard</h2>
                <div class="stats"><div class="stat"><b>{total}</b>Enrolled</div>
                <div class="stat"><b>{average}%</b>Average progress</div>
                <div class="stat"><b>{sum(r["progress"] == 100 for r in rows)}</b>Completed</div></div></section><br>
                <section class="grid">{cards or '<p class="muted">No enrollments yet. Visit the catalog to start learning.</p>'}</section>""",
                                user_id=user_id))
            elif parsed.path == "/add":
                self.send_html(page("""<h2>Add a coding tutorial</h2><form method="post" action="/add">
                <label>Title</label><input name="title" required><label>Description</label>
                <textarea name="description" required></textarea><label>YouTube URL</label>
                <input name="youtube_url" placeholder="https://youtu.be/..." required><label>Topic</label><input name="topic" required>
                <label>Level</label><select name="level"><option>Beginner</option><option>Intermediate</option><option>Advanced</option></select>
                <button>Save tutorial</button></form>""", user_id=self.current_user_id()))
            elif parsed.path == "/register":
                self.send_html(page("""<h2>Register learner</h2><form method="post" action="/register">
                <label>Name</label><input name="name" required><label>Email</label><input name="email" type="email" required>
                <label>Password (minimum 8 characters)</label><input name="password" type="password" minlength="8" required>
                <button>Register and open dashboard</button></form>""", user_id=self.current_user_id()))
            elif parsed.path == "/login":
                self.send_html(page("""<h2>Sign in</h2><form method="post" action="/login">
                <label>Email</label><input name="email" type="email" required>
                <label>Password</label><input name="password" type="password" required>
                <button>Sign in</button></form><p class="muted">Demo account: demo@learntube.local / demo-password</p>""",
                                user_id=self.current_user_id()))
            elif parsed.path == "/logout":
                cookie = SimpleCookie(self.headers.get("Cookie", ""))
                token = cookie.get("session")
                if token:
                    sessions.pop(token.value, None)
                self.send_html(page('<h2>Signed out</h2><a class="button" href="/">Return to catalogue</a>'),
                                headers={"Set-Cookie": "session=; Max-Age=0; HttpOnly; SameSite=Lax; Path=/"})
            else:
                self.send_html(page("<h2>Page not found</h2>"), 404)
        except (ValueError, TypeError) as error:
            self.send_html(page(f"<h2>Could not load page</h2><p>{esc(error)}</p>"), 400)

    def user_options(self) -> str:
        return "".join(f'<option value="{u["id"]}">{esc(u["name"])} (ID {u["id"]})</option>'
                       for u in repository.fetchall("SELECT id, name FROM users ORDER BY name"))

    def do_POST(self) -> None:
        length = int(self.headers.get("Content-Length", "0"))
        values = parse_qs(self.rfile.read(length).decode())
        try:
            if self.path == "/register":
                user = platform.add_user(value(values, "name"), value(values, "email"), value(values, "password"))
                token = secrets.token_urlsafe(32)
                sessions[token] = user.id
                self.send_html(page(f'<h2>Welcome, {esc(user.name)}</h2><p>Your private dashboard is ready.</p>'
                                    f'<a class="button" href="/dashboard/{user.id}">Open my dashboard</a>', "Learner registered."),
                                headers={"Set-Cookie": f"session={token}; HttpOnly; SameSite=Lax; Path=/"})
            elif self.path == "/add":
                tutorial = platform.add_tutorial(*(value(values, k) for k in ["title", "description", "youtube_url", "topic", "level"]))
                self.send_html(page(f'<h2>Tutorial saved</h2><p>{esc(tutorial.title)} is now available in the catalogue.</p>'
                                    '<a class="button" href="/">View catalogue</a>', "Tutorial added.",
                                    user_id=self.current_user_id()))
            elif self.path == "/enroll":
                user_id = self.require_user()
                if user_id is None:
                    return
                platform.enroll(user_id, int(value(values, "tutorial_id")))
                self.send_html(page(f'<h2>Enrollment complete</h2><a class="button" href="/dashboard/{user_id}">Open dashboard</a>',
                                    "Tutorial added to your dashboard.", user_id=user_id))
            elif self.path == "/progress":
                user_id = self.require_user()
                if user_id is None or user_id != int(value(values, "user_id")):
                    self.send_html(page("<h2>Forbidden</h2><p>You can only update your own progress.</p>"), 403)
                    return
                platform.update_progress(user_id, int(value(values, "tutorial_id")), int(value(values, "progress")))
                self.send_html(page(f'<h2>Progress updated</h2><a class="button" href="/dashboard/{user_id}">Return to dashboard</a>',
                                    "Progress saved.", user_id=user_id))
            elif self.path == "/note":
                user_id = self.require_user()
                if user_id is None or user_id != int(value(values, "user_id")):
                    self.send_html(page("<h2>Forbidden</h2><p>You can only save notes to your own dashboard.</p>"), 403)
                    return
                platform.add_note(user_id, int(value(values, "tutorial_id")), value(values, "body"))
                self.send_html(page(f'<h2>Note saved</h2><a class="button" href="/dashboard/{user_id}">Return to dashboard</a>',
                                    "Learning note saved.", user_id=user_id))
            elif self.path == "/login":
                user = platform.authenticate(value(values, "email"), value(values, "password"))
                if user is None:
                    self.send_html(page('<h2>Sign in failed</h2><p>Incorrect email or password.</p><a class="button" href="/login">Try again</a>'), 401)
                    return
                token = secrets.token_urlsafe(32)
                sessions[token] = user.id
                self.send_response(303)
                self.send_header("Location", f"/dashboard/{user.id}")
                self.send_header("Set-Cookie", f"session={token}; HttpOnly; SameSite=Lax; Path=/")
                self.end_headers()
            else:
                self.send_html(page("<h2>Page not found</h2>"), 404)
        except (ValueError, TypeError) as error:
            self.send_html(page(f"<h2>Could not complete request</h2><p>{esc(error)}</p>"), 400)

    def log_message(self, format: str, *args) -> None:
        print(format % args)


if __name__ == "__main__":
    seed_demo_data()
    print("LearnTube UI running at http://localhost:8000")
    ThreadingHTTPServer(("localhost", 8000), Handler).serve_forever()
