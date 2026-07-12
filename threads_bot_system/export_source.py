"""Load an explicitly selected Ready document from the local content vault."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


@dataclass(frozen=True, slots=True)
class ExportSource:
    content_id: str
    platform: str
    source_ref: str
    content_version: int
    scheduled_time: str | None
    body: str


def load_export_source(path: str | Path, ready_root: str | Path) -> ExportSource:
    source_path = Path(path).resolve()
    allowed_root = Path(ready_root).resolve()
    try:
        source_path.relative_to(allowed_root)
    except ValueError as exc:
        raise ValueError("Export source must be inside the Threads Ready directory") from exc

    fields, body = parse_frontmatter(source_path.read_text(encoding="utf-8"))
    content_id = fields.get("content_id", "").strip()
    platform = fields.get("platform", "").strip()
    status = (fields.get("editorial_status") or fields.get("status") or "").strip()
    source_ref = fields.get("source_ref", "").strip() or f"local:{content_id}"
    scheduled_time = fields.get("scheduled_time", "").strip() or None

    if not content_id:
        raise ValueError("Export source requires content_id")
    if platform != "threads":
        raise ValueError("Export source platform must be threads")
    if status != "ready":
        raise ValueError("Export source must be ready")
    if scheduled_time:
        _require_timezone(scheduled_time)

    try:
        content_version = int(fields.get("content_version", "1"))
    except ValueError as exc:
        raise ValueError("content_version must be an integer") from exc
    if content_version < 1:
        raise ValueError("content_version must be at least 1")

    cleaned_body = clean_obsidian_body(body)
    if not cleaned_body:
        raise ValueError("Export source body is empty")

    return ExportSource(
        content_id=content_id,
        platform=platform,
        source_ref=source_ref,
        content_version=content_version,
        scheduled_time=scheduled_time,
        body=cleaned_body,
    )


def parse_frontmatter(raw: str) -> tuple[dict[str, str], str]:
    lines = raw.splitlines()
    if not lines or lines[0].strip() != "---":
        raise ValueError("Source must start with frontmatter")
    try:
        end = next(index for index, line in enumerate(lines[1:], start=1) if line.strip() == "---")
    except StopIteration as exc:
        raise ValueError("Source frontmatter is not closed") from exc

    fields: dict[str, str] = {}
    for line in lines[1:end]:
        if ":" not in line:
            continue
        name, value = line.split(":", 1)
        fields[name.strip()] = value.strip()
    return fields, "\n".join(lines[end + 1 :]).strip()


def clean_obsidian_body(body: str) -> str:
    text = re.sub(r"%%.*?%%", "", body, flags=re.DOTALL)
    text = re.sub(r"!\[\[[^\]]+\]\]", "", text)
    text = re.sub(r"\[\[[^|\]]+\|([^\]]+)\]\]", r"\1", text)
    text = re.sub(r"\[\[([^\]]+)\]\]", r"\1", text)
    return "\n".join(line.rstrip() for line in text.splitlines()).strip()


def _require_timezone(value: str) -> None:
    normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise ValueError("scheduled_time must be ISO 8601") from exc
    if parsed.tzinfo is None:
        raise ValueError("scheduled_time must include a timezone")

