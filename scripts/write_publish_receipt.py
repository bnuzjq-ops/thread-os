from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path


def read_frontmatter(path: Path) -> dict[str, str]:
    lines = path.read_text(encoding="utf-8").splitlines()
    if not lines or lines[0].strip() != "---":
        raise ValueError(f"snapshot is missing frontmatter: {path}")
    end = next(i for i, line in enumerate(lines[1:], 1) if line.strip() == "---")
    return {key.strip(): value.strip() for key, value in (line.split(":", 1) for line in lines[1:end] if ":" in line)}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--state", required=True)
    parser.add_argument("--content-root", required=True)
    parser.add_argument("--snapshot-path", required=True)
    parser.add_argument("--task-id", required=True)
    args = parser.parse_args()
    state = json.loads(Path(args.state).read_text(encoding="utf-8"))
    task = state.get("tasks", {}).get(args.task_id)
    if not task and args.task_id.endswith(":v1"):
        task = state.get("tasks", {}).get(args.task_id[:-3])
    if not task:
        raise ValueError(f"publish task not found: {args.task_id}")
    root = Path(args.content_root)
    fields = read_frontmatter(root / args.snapshot_path)
    content_id = fields.get("content_id") or task.get("source_key")
    version = int(fields.get("content_version", "1"))
    receipt = root / "receipts" / "publishing" / f"{content_id}-v{version}.json"
    receipt.parent.mkdir(parents=True, exist_ok=True)
    receipt.write_text(json.dumps({
        "content_id": content_id,
        "content_version": version,
        "status": task.get("status"),
        "scheduled_time": task.get("scheduled_time") or fields.get("scheduled_time"),
        "published_at": task.get("updated_at"),
        "platform_post_id": task.get("post_id"),
        "permalink": task.get("permalink"),
        "error_type": task.get("error_type"),
        "last_error": task.get("last_error"),
        "source_snapshot": args.snapshot_path,
        "recorded_at": datetime.now(timezone.utc).isoformat(),
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
