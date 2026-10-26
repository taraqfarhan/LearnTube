import pytest
from learning_platform.repository import SQLiteRepository
from learning_platform.service import LearningPlatform
from learning_platform.youtube import VideoMetadata


class FakeVideoProvider:
    def fetch(self, url):
        return VideoMetadata("abc123", "https://www.youtube.com/embed/abc123")


@pytest.fixture
def platform():
    repository = SQLiteRepository(":memory:")
    yield LearningPlatform(repository, FakeVideoProvider())
    repository.close()


def test_add_tutorial_uses_provider_and_persists_embed_link(platform):
    tutorial = platform.add_tutorial("Python", "Basics", "https://youtu.be/ignored", "Python", "Beginner")
    assert tutorial.youtube_url.endswith("/abc123")
    assert platform.list_tutorials() == [tutorial]


def test_enrollment_and_progress_are_recorded(platform):
    user = platform.add_user("Ava", "ava@example.com")
    tutorial = platform.add_tutorial("Python", "Basics", "https://youtu.be/x", "Python", "Beginner")
    enrollment = platform.enroll(user.id, tutorial.id)
    assert platform.update_progress(user.id, tutorial.id, 60).progress == 60
    assert platform.dashboard(user.id) == [{"title": "Python", "topic": "Python", "progress": 60}]
    assert enrollment.progress == 0


def test_invalid_progress_is_rejected(platform):
    with pytest.raises(ValueError, match="between 0 and 100"):
        platform.update_progress(1, 1, 101)


def test_empty_note_is_rejected(platform):
    with pytest.raises(ValueError, match="cannot be empty"):
        platform.add_note(1, 1, " ")


def test_user_authentication_requires_correct_password(platform):
    user = platform.add_user("Ava", "ava-auth@example.com", "correct-password")
    assert platform.authenticate(user.email, "wrong-password") is None
    assert platform.authenticate(user.email, "correct-password").id == user.id


def test_short_password_is_rejected(platform):
    with pytest.raises(ValueError, match="at least 8 characters"):
        platform.add_user("Ava", "short@example.com", "short")


def test_dashboard_contains_only_the_authenticated_users_enrollments(platform):
    first_user = platform.add_user("Ava", "ava-dashboard@example.com", "password-one")
    second_user = platform.add_user("Ben", "ben-dashboard@example.com", "password-two")
    first_tutorial = platform.add_tutorial("Python", "Basics", "https://youtu.be/x", "Python", "Beginner")
    second_tutorial = platform.add_tutorial("NumPy", "Arrays", "https://youtu.be/y", "NumPy", "Beginner")
    platform.enroll(first_user.id, first_tutorial.id)
    platform.enroll(second_user.id, second_tutorial.id)

    assert [item["title"] for item in platform.dashboard_details(first_user.id)] == ["Python"]
    assert [item["title"] for item in platform.dashboard_details(second_user.id)] == ["NumPy"]


def test_tutorials_can_be_searched_by_keyword_and_level(platform):
    platform.add_tutorial("Python OOP", "Classes", "https://youtu.be/x", "Python", "Beginner")
    platform.add_tutorial("Advanced SQL", "Queries", "https://youtu.be/y", "Databases", "Advanced")
    results = platform.search_tutorials("python", "Beginner")
    assert [tutorial.title for tutorial in results] == ["Python OOP"]


def test_youtube_provider_rejects_non_youtube_url():
    from learning_platform.youtube import YouTubeProvider
    with pytest.raises(ValueError):
        YouTubeProvider().fetch("https://example.com/video")
