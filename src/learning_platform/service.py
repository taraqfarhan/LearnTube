"""Application services and validation rules."""

import sqlite3
import hashlib
import hmac
import secrets
from typing import Optional
from .models import Enrollment, Note, Tutorial, User
from .repository import SQLiteRepository
from .search import TutorialSearch
from .youtube import VideoProvider, YouTubeProvider


class LearningPlatform:
    """Coordinates users, tutorials, enrollments, notes, and video embeds."""

    def __init__(self, repository: SQLiteRepository, video_provider: Optional[VideoProvider] = None) -> None:
        self.repository = repository
        self.video_provider = video_provider or YouTubeProvider()

    def add_user(self, name: str, email: str, password: str = "demo-password") -> User:
        if not name.strip() or "@" not in email:
            raise ValueError("Name and valid email are required")
        if len(password) < 8:
            raise ValueError("Password must contain at least 8 characters")
        password_hash = self._hash_password(password)
        cursor = self.repository.execute(
            "INSERT INTO users(name, email, password_hash) VALUES (?, ?, ?)",
            (name.strip(), email.strip().lower(), password_hash),
        )
        return User(cursor.lastrowid, name.strip(), email.strip())

    @staticmethod
    def _hash_password(password: str, salt: bytes | None = None) -> str:
        salt = salt or secrets.token_bytes(16)
        digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 200_000)
        return f"{salt.hex()}${digest.hex()}"

    def authenticate(self, email: str, password: str) -> Optional[User]:
        row = self.repository.fetchone(
            "SELECT id, name, email, password_hash FROM users WHERE email = ?",
            (email.strip().lower(),),
        )
        if row is None or not row["password_hash"]:
            return None
        salt_hex, digest_hex = row["password_hash"].split("$", 1)
        expected = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt_hex), 200_000)
        if not hmac.compare_digest(expected.hex(), digest_hex):
            return None
        return User(row["id"], row["name"], row["email"])

    def add_tutorial(self, title: str, description: str, youtube_url: str, topic: str, level: str) -> Tutorial:
        video = self.video_provider.fetch(youtube_url)
        cursor = self.repository.execute(
            "INSERT INTO tutorials(title, description, youtube_url, topic, level) VALUES (?, ?, ?, ?, ?)",
            (title.strip(), description.strip(), video.embed_url, topic.strip(), level.strip()),
        )
        return Tutorial(cursor.lastrowid, title.strip(), description.strip(), video.embed_url, topic.strip(), level.strip())

    def list_tutorials(self) -> list[Tutorial]:
        rows = self.repository.fetchall("SELECT * FROM tutorials ORDER BY title")
        return [Tutorial(**dict(row)) for row in rows]

    def enroll(self, user_id: int, tutorial_id: int) -> Enrollment:
        try:
            cursor = self.repository.execute(
                "INSERT INTO enrollments(user_id, tutorial_id) VALUES (?, ?)", (user_id, tutorial_id)
            )
        except sqlite3.IntegrityError as error:
            raise ValueError("User or tutorial is invalid, or enrollment already exists") from error
        return Enrollment(cursor.lastrowid, user_id, tutorial_id)

    def update_progress(self, user_id: int, tutorial_id: int, progress: int) -> Enrollment:
        if not 0 <= progress <= 100:
            raise ValueError("Progress must be between 0 and 100")
        self.repository.execute(
            "UPDATE enrollments SET progress = ? WHERE user_id = ? AND tutorial_id = ?",
            (progress, user_id, tutorial_id),
        )
        row = self.repository.fetchone(
            "SELECT * FROM enrollments WHERE user_id = ? AND tutorial_id = ?", (user_id, tutorial_id)
        )
        if row is None:
            raise ValueError("Enrollment not found")
        return Enrollment(**dict(row))

    def add_note(self, user_id: int, tutorial_id: int, body: str) -> Note:
        if not body.strip():
            raise ValueError("Note cannot be empty")
        cursor = self.repository.execute(
            "INSERT INTO notes(user_id, tutorial_id, body) VALUES (?, ?, ?)",
            (user_id, tutorial_id, body.strip()),
        )
        return Note(cursor.lastrowid, user_id, tutorial_id, body.strip())

    def dashboard(self, user_id: int) -> list[dict]:
        return [dict(row) for row in self.repository.fetchall(
            """SELECT t.title, t.topic, e.progress FROM enrollments e
               JOIN tutorials t ON t.id = e.tutorial_id WHERE e.user_id = ?""", (user_id,)
        )]

    def dashboard_details(self, user_id: int) -> list[dict]:
        return [dict(row) for row in self.repository.fetchall(
            """SELECT t.id AS tutorial_id, t.title, t.topic, t.youtube_url, e.progress,
                      (SELECT n.body FROM notes n WHERE n.user_id = e.user_id
                       AND n.tutorial_id = e.tutorial_id ORDER BY n.id DESC LIMIT 1) AS note
               FROM enrollments e JOIN tutorials t ON t.id = e.tutorial_id
               WHERE e.user_id = ? ORDER BY t.title""", (user_id,)
        )]

    def search_tutorials(self, keyword: str = "", level: Optional[str] = None) -> list[Tutorial]:
        results = TutorialSearch(self.list_tutorials()).by_keyword(keyword) if keyword else self.list_tutorials()
        return TutorialSearch(results).by_level(level) if level else results
