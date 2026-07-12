# 当前上下文

## 已确认的架构边界

- GitHub Actions 继续负责调用 DeepSeek、飞书和 Threads。
- D1 只负责保存回复任务的运行时状态。
- GitHub 仓库不再作为未来生产任务数据库。
- 现有 Feishu Callback Worker 保持不动。
- 新 State Worker 必须和 Feishu Callback Worker 分开。
- 当前系统仍然只做半自动回复。

## 本轮改造范围

- 只改本地存储层抽象。
- 先建立统一的 `TaskStore`。
- 先让现有 JSON 存储实现这个接口。
- 先验证现有 Python 单测全部通过。
- 本轮不接入远程 D1。

## 当前状态

- 现有回复链路已经有本地 JSON 状态文件实现。
- 业务代码正在切换到统一存储接口。
- 后续再接 State Worker 和 D1。

## 已阅读的 Cloudflare 官方文档

- D1 Getting started
- D1 Worker Binding API
- D1Database binding
- Prepared statements and bind
- Local development
- Migrations
- Wrangler D1 commands
- Build an API to access D1 using a proxy Worker
- Query D1 Database HTTP API
- D1 pricing and limits

## 本机敏感信息索引

- Cloudflare D1 API 令牌：`C:\Users\bnuzj\Documents\Jq\敏感信息\Threads助手CloudflareD1配置.md`
## Publish lane

- Added a JSON-backed publish queue, generic Threads publish support, a `publish` CLI command, and `.github/workflows/publish.yml`.
- Still on JSON for now; remind the user later to migrate publish state to State API.

## JSON business closure status

- JSON is the only current runtime backend; D1 and State API remain deferred migration targets.
- Publish accepts a Markdown source with `content_id`, `platform: threads`, `status: ready`, and a non-empty body via `publish --source`.
- Publish uses `ready -> publishing -> published`; explicit failures are `failed`, and uncertain timeouts are `unknown`.
- DeepSeek failures are recorded as `failed`; uncertain Threads reply results are recorded as `unknown`.
- Successful dispatch can send a separate Feishu text result after `reply_id` is persisted.
- Local verification currently has 52 passing Python tests; this does not prove real external integration.

## 暂停点 / 2026-07-11

- 当前任务已按用户要求暂停。
- 已完成的最新内容：补上了发布链路的最小闭环，包含 JSON-backed publish store、Threads 通用发帖接口、`publish` CLI、`publish.yml` 工作流。
- 验证结果：`python -m unittest discover -s tests` 通过，当前全量单测为 52 passed。
- 当前仍未完成：发布任务还只是 JSON 存储，后续必须迁到 State API / D1；发布源契约已建立，但尚未接入真实内容仓库。
- 本轮没有修改 Feishu Callback Worker，也没有做远程部署或真实联调。
- 后续恢复任务时，优先查看 `RESTART_HANDOFF.md`、`README.md`、`ARCHITECTURE.md`、`RUNBOOK.md`、`SPEC.md` 和本文件。

## Three-repository decision（2026-07-12）

- A is `C:\jq\OBS`, remains local-only, and is the complete content source of truth.
- B is the private `bnuzjq-ops/threads-publish-feed`; it stores only approved publish snapshots.
- C is `bnuzjq-ops/thread-os`; it reads B but never reads A.
- The only write path into B is the explicit `export-content` command after user approval.
- GitHub Actions uses `CONTENT_REPO` and read-only `CONTENT_REPO_TOKEN` for B.
- Publish and reply runtime state remain JSON in C. D1 is deferred.
- The B test snapshot intentionally has no `scheduled_time`; it cannot be selected by cron.
- No real Threads publish, Feishu card delivery, Worker deployment, Secret update, or main merge was authorized in this phase.
