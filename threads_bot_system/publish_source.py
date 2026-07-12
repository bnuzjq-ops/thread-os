"""Read the minimal Markdown contract for a publish task."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class PublishSource:
    """A ready Threads post loaded from Markdown."""

    content_id: str
    platform: str
    status: str
    text: str


def load_publish_source(path: str | Path) -> PublishSource:
    """Load a ready Markdown source with the project frontmatter contract."""
    raw = Path(path).read_text(encoding="utf-8")
    lines = raw.splitlines()
    if not lines or lines[0].strip() != "---":
        raise ValueError("Publish source must start with frontmatter")

    try:
        end = next(index for index, line in enumerate(lines[1:], start=1) if line.strip() == "---")
    except StopIteration as exc:
        raise ValueError("Publish source frontmatter is not closed") from exc

    fields: dict[str, str] = {}
    for line in lines[1:end]:
        if ":" not in line:
            continue
        name, value = line.split(":", 1)
        fields[name.strip()] = value.strip()

    content_id = fields.get("content_id", "").strip()
    platform = fields.get("platform", "").strip()
    status = fields.get("status", fields.get("editorial_status", "")).strip()
    text = "\n".join(lines[end + 1:]).strip()
    if not content_id:
        raise ValueError("Publish source requires content_id")
    if platform != "threads":
        raise ValueError("Publish source platform must be threads")
    if status != "ready":
        raise ValueError("Publish source status must be ready")
    if not text:
        raise ValueError("Publish source body is empty")

    return PublishSource(content_id=content_id, platform=platform, status=status, text=text)
