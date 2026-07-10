"""Project contract and boundary manifest for the Threads rebuild."""

from __future__ import annotations

from pathlib import Path

PROJECT_NAME = "Threads 自动化系统 V2"
EXECUTION_REPO_ROOT = Path(__file__).resolve().parents[1]
CONTENT_REPO_ROOT = Path(r"C:\jq\OBS\threads-system")
LEGACY_REPO_ROOT = Path(r"C:\jq\AI\threads-bot os")


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
                "执行仓库",
                "Threads API",
                "状态记录",
            ],
            "reply": [
                "评论监控",
                "草稿生成",
                "飞书审核",
                "Cloudflare Worker",
                "GitHub dispatch",
                "reply-action",
                "Threads API",
            ],
        },
        "boundaries": [
            "content_repo is for素材、草稿、待发布内容",
            "execution_repo is for automation code, tests, state, and docs",
            "legacy_repo is read-only reference only",
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
