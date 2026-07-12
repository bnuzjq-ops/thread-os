"""Select one approved publish snapshot from the read-only content feed."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from .publish_source import PublishSource, load_publish_source


def select_manual_source(queue_dir: str | Path, content_id: str) -> PublishSource:
    normalized_id = str(content_id).strip()
    if not normalized_id or Path(normalized_id).name != normalized_id:
        raise ValueError("Manual publish requires a valid content_id")

    source = load_publish_source(Path(queue_dir) / f"{normalized_id}.md")
    if source.content_id != normalized_id:
        raise ValueError("Publish snapshot content_id does not match its filename")
    return source


def select_scheduled_source(
    queue_dir: str | Path,
    *,
    now: datetime | None = None,
) -> PublishSource | None:
    current_time = now or datetime.now().astimezone()
    if current_time.tzinfo is None:
        raise ValueError("Scheduled selection time must include a timezone")

    eligible: list[tuple[datetime, str, PublishSource]] = []
    for path in sorted(Path(queue_dir).glob("*.md")):
        source = load_publish_source(path)
        if not source.scheduled_time:
            continue
        scheduled_time = _parse_scheduled_time(source.scheduled_time)
        if scheduled_time <= current_time:
            eligible.append((scheduled_time, source.content_id, source))

    if not eligible:
        return None
    eligible.sort(key=lambda item: (item[0], item[1]))
    return eligible[0][2]


def _parse_scheduled_time(value: str) -> datetime:
    normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise ValueError("scheduled_time must be ISO 8601") from exc
    if parsed.tzinfo is None:
        raise ValueError("scheduled_time must include a timezone")
    return parsed
