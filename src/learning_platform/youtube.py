"""YouTube integration boundary."""

from dataclasses import dataclass
from urllib.parse import parse_qs, urlparse
from typing import Protocol


@dataclass(frozen=True)
class VideoMetadata:
    video_id: str
    embed_url: str


class VideoProvider(Protocol):
    def fetch(self, url: str) -> VideoMetadata: ...


class YouTubeProvider:
    """Extracts a safe embeddable YouTube URL without requiring an API key."""

    def fetch(self, url: str) -> VideoMetadata:
        parsed = urlparse(url)
        video_id = parse_qs(parsed.query).get("v", [None])[0]
        if parsed.hostname in {"youtu.be"}:
            video_id = parsed.path.strip("/")
        elif parsed.hostname not in {"youtube.com", "www.youtube.com", "m.youtube.com"}:
            video_id = None
        if not video_id or len(video_id) > 20 or not video_id.replace("-", "").replace("_", "").isalnum():
            raise ValueError("A valid YouTube URL is required")
        return VideoMetadata(video_id, f"https://www.youtube.com/embed/{video_id}")
