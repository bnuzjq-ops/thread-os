"""Read the minimal Markdown contract for a publish task."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


@dataclass(frozen=True, slots=True)
class PublishSource:
    """A ready Threads post loaded from Markdown."""

    content_id: str
    platform: str
    status: str
    text: str
    content_version: int = 1
    scheduled_time: str | None = None


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

    try:
        content_version = int(fields.get("content_version", "1"))
    except ValueError as exc:
        raise ValueError("content_version must be a positive integer") from exc
    if content_version < 1:
        raise ValueError("content_version must be a positive integer")

    scheduled_time = fields.get("scheduled_time", "").strip() or None
    if scheduled_time is not None:
        try:
            parsed = datetime.fromisoformat(scheduled_time.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValueError("scheduled_time must be ISO 8601") from exc
        if parsed.tzinfo is None:
            raise ValueError("scheduled_time must include a timezone")

    return PublishSource(
        content_id=content_id,
        platform=platform,
        status=status,
        text=text,
        content_version=content_version,
        scheduled_time=scheduled_time,
    )


def select_due_source(root: str | Path, now: datetime | None = None) -> Path | None:
    """Select the earliest due scheduled source, stably ordered by content ID."""
    duplicates = find_duplicate_scheduled_times(root)
    if duplicates:
        details = "; ".join(f"{when}: {', '.join(ids)}" for when, ids in duplicates.items())
        raise ValueError(f"duplicate scheduled_time; reschedule before publishing: {details}")
    current = now or datetime.now(timezone.utc)
    if current.tzinfo is None:
        raise ValueError("now must include a timezone")
    current = current.astimezone(timezone.utc)
    candidates: list[tuple[datetime, str, Path]] = []
    for path in sorted(Path(root).glob("*.md")):
        source = load_publish_source(path)
        if not source.scheduled_time:
            continue
        scheduled = datetime.fromisoformat(source.scheduled_time.replace("Z", "+00:00"))
        if scheduled.astimezone(timezone.utc) <= current:
            candidates.append((scheduled.astimezone(timezone.utc), source.content_id, path))
    if not candidates:
        return None
    candidates.sort(key=lambda item: (item[0], item[1]))
    return candidates[0][2]


def find_duplicate_scheduled_times(root: str | Path) -> dict[str, list[str]]:
    """Return scheduled timestamps that are assigned to more than one source."""
    by_time: dict[str, list[str]] = {}
    for path in sorted(Path(root).glob("*.md")):
        source = load_publish_source(path)
        if source.scheduled_time:
            by_time.setdefault(source.scheduled_time, []).append(source.content_id)
    return {when: ids for when, ids in by_time.items() if len(ids) > 1}
