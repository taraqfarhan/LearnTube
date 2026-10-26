"""Search strategy implementations."""

from typing import Iterable
from .models import Tutorial


class TutorialSearch:
    """Structural Facade over tutorial filtering."""

    def __init__(self, tutorials: Iterable[Tutorial]) -> None:
        self.tutorials = list(tutorials)

    def by_keyword(self, keyword: str) -> list[Tutorial]:
        needle = keyword.strip().lower()
        return [
            item for item in self.tutorials
            if needle in f"{item.title} {item.description} {item.topic}".lower()
        ]

    def by_level(self, level: str) -> list[Tutorial]:
        return [item for item in self.tutorials if item.level.lower() == level.lower()]
