"""Export an approved local content snapshot into the publish feed repository."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import subprocess

from .export_source import ExportSource, load_export_source
from .publish_source import load_publish_source


@dataclass(frozen=True, slots=True)
class ExportResult:
    target_path: Path
    content_id: str
    content_version: int


def export_content(
    source_path: str | Path,
    feed_repo: str | Path,
    *,
    ready_root: str | Path,
    replace: bool = False,
    exported_at: str | None = None,
) -> ExportResult:
    source = load_export_source(source_path, ready_root)
    queue_dir = Path(feed_repo) / "posts" / "queue"
    target_path = queue_dir / f"{source.content_id}.md"
    content_version = source.content_version

    if target_path.exists():
        if not replace:
            raise FileExistsError(f"Publish snapshot already exists: {source.content_id}")
        existing = load_publish_source(target_path)
        content_version = existing.content_version + 1

    timestamp = exported_at or datetime.now().astimezone().isoformat(timespec="seconds")
    queue_dir.mkdir(parents=True, exist_ok=True)
    target_path.write_text(
        _render_snapshot(source, content_version=content_version, exported_at=timestamp),
        encoding="utf-8",
    )
    return ExportResult(
        target_path=target_path,
        content_id=source.content_id,
        content_version=content_version,
    )


def ensure_feed_repo_clean(feed_repo: str | Path) -> None:
    repo = Path(feed_repo).resolve()
    if not (repo / ".git").exists():
        raise ValueError(f"Publish feed is not a Git repository: {repo}")
    result = _run_git(repo, "status", "--porcelain")
    if result.stdout.strip():
        raise RuntimeError("Publish feed has existing uncommitted changes")


def push_export(feed_repo: str | Path, result: ExportResult) -> None:
    repo = Path(feed_repo).resolve()
    target = result.target_path.resolve()
    try:
        relative_target = target.relative_to(repo)
    except ValueError as exc:
        raise ValueError("Export target must be inside the publish feed repository") from exc

    _run_git(repo, "add", "--", relative_target.as_posix())
    _run_git(repo, "commit", "-m", f"content: queue {result.content_id}")
    _run_git(repo, "push", "origin", "HEAD:main")


def _run_git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    )


def _render_snapshot(source: ExportSource, *, content_version: int, exported_at: str) -> str:
    lines = [
        "---",
        f"content_id: {source.content_id}",
        "platform: threads",
        "editorial_status: ready",
    ]
    if source.scheduled_time:
        lines.append(f"scheduled_time: {source.scheduled_time}")
    lines.extend(
        [
            f"source_ref: {source.source_ref}",
            f"content_version: {content_version}",
            f"exported_at: {exported_at}",
            "---",
            "",
            source.body,
            "",
        ]
    )
    return "\n".join(lines)
