# 运行手册

## 开工前

1. 读 `README.md`
2. 读 `SPEC.md`
3. 读 `ARCHITECTURE.md`
4. 确认当前修改只影响目标链路

## 本地验证

- 先看 `git status`
- 再跑单元测试
- 再跑最小烟雾测试

## 修改原则

- 每次只改一个清晰的点
- 不重构无关文件
- 不碰旧仓库
- 不输出 secret

## 外部平台变更前

- 先确认当前用的是哪条链路
- 先确认对应的回调、Secret 和仓库目标
- 先写契约，再改实现

## 这套自动回复现在会用到的变量

- `FEISHU_APP_ID`
- `FEISHU_APP_SECRET`
- `FEISHU_CHAT_ID`
- `DEEPSEEK_API_KEY`
- `DEEPSEEK_MODEL`，可选，默认 `deepseek-v4-flash`
- `DEEPSEEK_BASE_URL`，可选，默认 `https://api.deepseek.com`
- `THREADS_ACCESS_TOKEN`
- `THREADS_USER_ID`
- `THREADS_STORE_PATH`，可选，默认 `state/reply_tasks.json`
- `THREADS_MONITOR_CURSOR_PATH`，可选，默认 `state/reply_monitor_cursor.json`

监控入口会先按 `THREADS_USER_ID` 自动拉取当前用户的 Threads 帖子，再去扫每条帖子的回复；`--media-id` 仅保留给手动临时指定单帖扫描。
首次运行只记录当前已知评论的最新时间作为基线，不向飞书发送历史评论；之后只处理时间戳晚于游标的新评论。监控也会跳过你已经在 Threads 里自己回复过的顶层评论，以及已经进入稳定状态的任务。
游标文件和 `state/reply_tasks.json` 必须一起提交，不能只更新其中一个。

## Cloudflare Worker 仍然需要的变量

- `FEISHU_VERIFICATION_TOKEN`
- `GITHUB_PAT`
- `GITHUB_REPO`
- `GITHUB_DISPATCH_EVENT`，可选，默认 `threads_reply_action`

## 失败处理

- 先判断是配置、权限、代码还是外部平台问题
- 不要重复试错同一条路径
- 保留错误输出和复现步骤

### publishing 长期卡住

任务卡在 `publishing` 状态说明 `claim_publish()` 执行了但 `complete_publish()` 未完成（进程崩溃、网络中断等）。恢复步骤：

1. 检查 Threads 页面是否实际产生了新帖子
2. **如果有新帖**：记下 Threads post ID，手动编辑 `state/publish_tasks.json`，将该任务状态改为 `published`，填入 `platform_post_id`，并更新 `updated_at` 时间戳
3. **如果没有新帖**：手动将状态改回 `ready`，next run 会重新选取
4. 千万**不要**手动重发——如果 Threads 已经有内容但你没找到，会产生重复帖

### sending 长期卡住

任务卡在 `sending` 状态：`claim_send()` 执行了但 `complete_send()` 未完成。恢复步骤：

1. 检查 Threads 帖子的回复区，确认是否已出现该条回复
2. **如果已回复**：记下 Threads reply_id，手动编辑 `state/reply_tasks.json`，将该任务状态改为 `sent`，填入 `reply_id`，更新时间戳
3. **如果没有回复**：将状态改回 `awaiting_review`，飞书审核卡片仍然有效，可重新点击 send
4. **如果无法确定**：标记为 `unknown`，等对账确认

### Threads 成功但 JSON 未更新（补记）

如果 Threads 侧已经有了帖子或回复，但 JSON 中的状态未同步：

1. 从对应 workflow run 下载 `*-state-recovery-*` artifact（保留 7 天）
2. 打开 artifact 中的 `state/publish_tasks.json` 或 `state/reply_tasks.json`，找到对应任务记录
3. **发布补记**：将 `status` 改为 `published`，填入 `platform_post_id` 和 Threads 链接
4. **回复补记**：将 `status` 改为 `sent`，填入 `reply_id`
5. 手动 commit 更新后的 JSON 到仓库
6. 不要删除原始 recovery artifact——它记录了补记之前的状态

### Token 更新

Token 更新不会导致重复发布或回复，因为状态机通过以下机制保证幂等：

- `published` 状态的任务不会被重新选取（`_select_tasks()` 只选 `ready`）
- `sent` 状态的任务在 dispatch 入口直接返回（`execute_reply_dispatch()` 显式短路）
- `claim_send()` 要求状态为 `awaiting_review` 且 `draft_version` 匹配
- `claim_publish()` 要求状态为 `ready`

更新 Token 的步骤：

1. 在 GitHub Settings → Secrets 中更新对应 Secret
2. 如果是 Threads Token（`THREADS_ACCESS_TOKEN`）：观察下一个 schedule run，确认 `comments` 正常返回
3. 如果是 GitHub PAT（`GITHUB_PAT`）：触发一次 `workflow_dispatch` 验证
4. JSON 状态**不需要**任何修改

### Git 冲突处理

如果 workflow 的 commit push 与手动 commit 产生冲突：

1. 冲突只可能发生在 `state/*.json` 文件上
2. 解决步骤：
   a. `git pull origin main` 获取最新状态
   b. 查看冲突文件：两个版本中哪个 `updated_at` 更新的保留，另一个是旧状态
   c. 对于 `state/reply_tasks.json`：合并两个版本的 `tasks` 字典，保留 `updated_at` 更晚的每个任务版本
   d. 对于 `state/publish_tasks.json`：同上
   e. 对于 `state/reply_monitor_cursor.json`：保留时间戳更新的版本
3. 解决后 `git add` + `git commit` + `git push`
4. 如果无法自行判断：下载对应 workflow run 的 recovery artifact 作为参考

## JSON MVP 验证

```text
python -m unittest discover -s tests
python -m threads_bot_system publish --help
```

`publish --source path/to/post.md` 会创建或复用一个 JSON 发布任务。明确 API 错误进入 `failed`，结果不确定的超时进入 `unknown`，两者都不会被自动重试。回复链路同样遵循此规则，并且发送前必须经过飞书人工确认。

## Publish feed export

Export an approved Obsidian draft explicitly; do not synchronize the whole vault:

```powershell
& .\scripts\export-threads-post.ps1 `
  -Source 'C:\jq\OBS\Threads\20_Drafts\example.md' `
  -ContentId 'stable-content-id'
```

The source must contain `platform: threads` and `editorial_status: ready`. The exporter writes only `posts/queue/<content_id>.md` to `bnuzjq-ops/threads-publish-feed`.

Scheduled runs use `scheduled_time` as timezone-aware ISO 8601, compare in UTC, select the earliest due source, and publish at most one item. Sources without `scheduled_time` are manual-only.

After publishing, inspect `state/publish_tasks.json`. A successful task has `status: published`, `post_id`/`platform_post_id`, and normally `permalink`. A permalink lookup failure must not trigger another publish.

For `failed` or `unknown`, inspect `error_type`, `error_phase`, `external_action`, `retry_allowed`, and `recovery_action`. `unknown` always requires checking Threads by ID before any manual action; it is never automatically retried.

If `state/publish_tasks.json` or `state/reply_tasks.json` is invalid JSON, stop the workflow and preserve the file for diagnosis. Do not delete it or rerun a publish. Restore from the last known-good Git commit, then inspect Threads by platform ID before any manual recovery.

If Git push fails, download the run's `*-state-recovery-*` artifact before recovery. Treat it as the runner's latest state snapshot; inspect external platform results before manually recording or retrying anything.

Reply dry-run sets `dry_run: true` in the dispatch payload. It records a `dry-run:<task_id>` result and sends a Feishu test receipt without calling the Threads reply API.

The code-level reply checks are covered by `tests/test_reply_runtime.py`, `tests/test_task_store_contract.py`, `tests/test_feishu_api.py`, and `tests/reply_worker.test.mjs`. These tests do not prove a live Feishu callback or a real Threads reply.

GitHub Actions 当前通过共享并发组和 commit 回写 JSON，这是 MVP 过渡方案，不是最终生产数据库架构；后续仍需迁移到 State API/D1。
