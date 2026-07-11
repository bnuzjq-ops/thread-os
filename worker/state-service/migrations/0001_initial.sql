CREATE TABLE reply_tasks (
    task_id TEXT PRIMARY KEY,
    comment_id TEXT NOT NULL UNIQUE,
    media_id TEXT NOT NULL,

    status TEXT NOT NULL,

    draft TEXT,
    draft_version INTEGER NOT NULL DEFAULT 0,
    draft_source TEXT,

    feishu_message_id TEXT,
    reply_id TEXT,

    claimed_at TEXT,
    lease_until TEXT,
    claimed_by TEXT,

    last_error TEXT,
    requires_manual_check INTEGER NOT NULL DEFAULT 0,

    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX idx_reply_tasks_status
ON reply_tasks(status);

CREATE TABLE task_events (
    event_id TEXT PRIMARY KEY,
    task_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    from_status TEXT,
    to_status TEXT,
    detail TEXT,
    created_at TEXT NOT NULL
);

CREATE INDEX idx_task_events_task_id
ON task_events(task_id);
