"""SQLite persistence adapter."""

import sqlite3
import threading
from typing import Any, Iterable, Optional


class SQLiteRepository:
    """Stores platform data in SQLite and exposes small query methods."""

    def __init__(self, path: str = "learning_platform.db") -> None:
        self.lock = threading.RLock()
        self.connection = sqlite3.connect(path, check_same_thread=False)
        self.connection.row_factory = sqlite3.Row
        self.initialize()

    def initialize(self) -> None:
        self.connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE, password_hash TEXT NOT NULL DEFAULT ''
            );
            CREATE TABLE IF NOT EXISTS tutorials (
                id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL,
                description TEXT NOT NULL, youtube_url TEXT NOT NULL,
                topic TEXT NOT NULL, level TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS enrollments (
                id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL,
                tutorial_id INTEGER NOT NULL, progress INTEGER NOT NULL DEFAULT 0,
                UNIQUE(user_id, tutorial_id),
                FOREIGN KEY(user_id) REFERENCES users(id),
                FOREIGN KEY(tutorial_id) REFERENCES tutorials(id)
            );
            CREATE TABLE IF NOT EXISTS notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL,
                tutorial_id INTEGER NOT NULL, body TEXT NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(id),
                FOREIGN KEY(tutorial_id) REFERENCES tutorials(id)
            );
            """
        )
        columns = {row["name"] for row in self.connection.execute("PRAGMA table_info(users)")}
        if "password_hash" not in columns:
            self.connection.execute("ALTER TABLE users ADD COLUMN password_hash TEXT NOT NULL DEFAULT ''")
        self.connection.commit()

    def execute(self, query: str, values: Iterable[Any] = ()) -> sqlite3.Cursor:
        with self.lock:
            cursor = self.connection.execute(query, tuple(values))
            self.connection.commit()
            return cursor

    def fetchone(self, query: str, values: Iterable[Any] = ()) -> Optional[sqlite3.Row]:
        with self.lock:
            return self.connection.execute(query, tuple(values)).fetchone()

    def fetchall(self, query: str, values: Iterable[Any] = ()) -> list[sqlite3.Row]:
        with self.lock:
            return self.connection.execute(query, tuple(values)).fetchall()

    def close(self) -> None:
        self.connection.close()
