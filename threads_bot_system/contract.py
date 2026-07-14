"""Project contract and boundary manifest for the Threads rebuild."""

from __future__ import annotations

import os
from pathlib import Path

PROJECT_NAME = "Threads 自动化系统 V2"
EXECUTION_REPO_ROOT = Path(__file__).resolve().parents[1]
CONTENT_REPO_ROOT = Path(os.environ.get("CONTENT_LIBRARY_ROOT", "D:/Obsidian/Work/Content Library"))
PUBLISH_FEED_ROOT = Path(os.environ.get("PUBLISH_FEED_ROOT", "C:/jq/AI/Thread OS/Threads-publish-feed"))
LEGACY_REPO_ROOT = Path(os.environ.get("LEGACY_REPLY_REPO_ROOT", "legacy-reply-system"))


def project_manifest() -> dict[str, object]:
    """Return the canonical project boundary manifest."""
    return {
        "project_name": PROJECT_NAME,
        "execution_repo_root": str(EXECUTION_REPO_ROOT),
        "content_repo_root": str(CONTENT_REPO_ROOT),
        "legacy_repo_root": str(LEGACY_REPO_ROOT),
        "chains": {
            "publish": [
                "内容仓库",
                "发布快照仓库",
                "执行仓库",
                "Threads API",
                "状态记录",
            ],
            "reply": [
                "冻结的评论监控",
                "冻结的草稿生成",
                "冻结的飞书审核",
                "Cloudflare Worker retained",
                "GitHub dispatch disabled for replies",
                "manual recovery only",
                "Threads reply API not called automatically",
            ],
        },
        "boundaries": [
            "content_repo is the formal Content Library source of truth",
            "publish_feed stores exported approved/scheduled snapshots only",
            "execution_repo is for automation code, tests, state, and docs",
            "legacy auto-reply code is frozen unless manually recovered",
            "secrets do not belong in git",
        ],
    }


def render_project_summary() -> str:
    """Render a compact human-readable summary for the CLI."""
    manifest = project_manifest()
    chains = manifest["chains"]
    boundaries = manifest["boundaries"]

    lines = [
        manifest["project_name"],
        f"执行仓库: {manifest['execution_repo_root']}",
        f"内容仓库: {manifest['content_repo_root']}",
        f"发布快照仓库: {PUBLISH_FEED_ROOT}",
        f"旧仓库: {manifest['legacy_repo_root']}",
        "",
        "发布链路:",
        " -> ".join(chains["publish"]),
        "",
        "回复链路:",
        " -> ".join(chains["reply"]),
        "",
        "边界:",
    ]
    lines.extend(f"- {item}" for item in boundaries)
    return "\n".join(lines)
