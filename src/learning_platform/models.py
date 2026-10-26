"""Domain entities for the learning platform."""

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class Tutorial:
    id: Optional[int]
    title: str
    description: str
    youtube_url: str
    topic: str
    level: str


@dataclass(frozen=True)
class User:
    id: Optional[int]
    name: str
    email: str


@dataclass(frozen=True)
class Enrollment:
    id: Optional[int]
    user_id: int
    tutorial_id: int
    progress: int = 0


@dataclass(frozen=True)
class Note:
    id: Optional[int]
    user_id: int
    tutorial_id: int
    body: str
