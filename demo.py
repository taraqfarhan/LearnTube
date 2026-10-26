"""Interactive demonstration of the LearnTube platform."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from learning_platform import LearningPlatform
from learning_platform.repository import SQLiteRepository


def main() -> None:
    platform = LearningPlatform(SQLiteRepository(":memory:"))

    user = platform.add_user("Ayesha", "ayesha@example.com")
    tutorial = platform.add_tutorial(
        "Python OOP",
        "Learn classes and objects",
        "https://www.youtube.com/watch?v=abc123",
        "Python",
        "Beginner",
    )

    platform.enroll(user.id, tutorial.id)
    platform.update_progress(user.id, tutorial.id, 60)
    platform.add_note(user.id, tutorial.id, "Review inheritance next.")

    print("User:", user)
    print("Tutorial:", tutorial)
    print("Embed link:", tutorial.youtube_url)
    print("Search results:", platform.search_tutorials("python", "Beginner"))
    print("Dashboard:", platform.dashboard(user.id))


if __name__ == "__main__":
    main()
