# Threads 系统交接

> 更新：2026-07-15。新 Agent 或新对话先读本文件，再按需读取下方文档。
>
> ⚠️ **2026-07-15 重要更新**：`@jq.sifu` 封禁已确认 Meta 官方大面积误封，账号已恢复。
> 当前主账号 `@jq.sifu`（User ID `27382011494786050`），长效 Token 60 天有效（至 2026-09-13）。
> 备用账号 `@qq.sifu`（User ID `27572263929068860`）Token 保留本地。
> 事故复盘见 [INCIDENT_THREADS_ACCOUNT_BAN_2026-07-15.md](INCIDENT_THREADS_ACCOUNT_BAN_2026-07-15.md)。
> 生产安全规则见 [PRODUCTION_SAFETY.md](PRODUCTION_SAFETY.md)。**所有 Agent 必须先读这两个文件。**

## 1. 系统边界

### 内容资产主库

- 本地：`D:\Obsidian\Threads os`
- GitHub：`bnuzjq-ops/threads-content-library`
- 保存原稿、版本、排期、发布快照和发布回执。
- 正式排期内容放在 `content/scheduled/`。

### 执行系统

- 本地：`C:\jq\AI\Thread OS\Threads-bot system`
- GitHub：`bnuzjq-ops/thread-os`
- 保存发布代码、GitHub Actions、Cloudflare Scheduler、测试和运行状态。
- 不作为内容资产库。

### 历史仓库

- `C:\jq\AI\Thread OS\Threads-publish-feed`
- `bnuzjq-ops/threads-publish-feed`

以上仅作历史参考，不是当前生产入口。

## 2. 当前发布流程

```text
D:\Obsidian\Threads os\content\scheduled\<content_id>.md
-> 推送 threads-content-library
-> 导出发布快照到 publish-feed/posts/queue/
-> 为该内容注册独立 Cloudflare Workflow
-> 到 scheduled_time 后触发 GitHub repository_dispatch
-> thread-os 只读取指定快照并调用 Threads API
-> 运行状态写入 state/publish_tasks.json
-> 发布回执写入内容库 receipts/publishing/
```

核心规则：

- `scheduled_time` 必须是带时区的 ISO 8601。
- 每篇排期内容对应一个独立 Workflow 实例，不使用固定 Cron 扫描全队列。
- GitHub 每次只处理 dispatch 指定的一篇，禁止顺带发布其他内容。
- 发布结果不写入正文，只写运行状态和独立回执。
- `published`、`unknown` 不自动重试；错过时间也不自动补发。

## 3. 当前真实状态

> ✅ 主账号 `@jq.sifu`（User ID `27382011494786050`）误封解除已恢复，长效 Token 60 天有效（至 2026-09-13）。GitHub Secrets 已更新。
> ✅ 备用账号 `@qq.sifu`（User ID `27572263929068860`）Token 保留本地。
> 当前发布链路已关闭真实发布（`PUBLISH_ENABLED=false`），待用户发起第一次灰度发布。

- 动态定时发布单条真实闭环曾经通过验证（历史）。
- 验证内容：`12345`（事故前最后一次测试）。
- 实际发布时间：2026-07-14 22:50（北京时间，历史）。
- Threads 帖子（旧账号，已不可访问）：`https://www.threads.com/@jq.sifu/post/DaxvqWGGuih`
- `platform_post_id`：`17993392871798071`（旧账号）
- GitHub 结果：`attempted: 1`、`posted: 1`（历史）。
- 执行状态：`published`（旧账号状态，仅保留审计）。
- 内容库已生成发布回执。
- 自动回复系统仍冻结，不参与当前发布流程。

2026-07-14 已修复的两个线上问题：

1. Workflow 到点醒来后不再重复执行“至少提前 5 分钟”校验；该校验只在注册时执行。
2. Cloudflare 的 GitHub 凭证已更新并通过 HTTP 200 鉴权验证。

注意：Cloudflare Workflow 实例固定使用创建时的代码版本。修复 Worker 后，旧等待实例不会自动升级，必须迁移到新实例。

## 4. 当前排期

- 22:05、22:35 两条因旧 Workflow / 旧凭证失败，未自动补发。
- 23:05、23:35、次日 00:05 三条已迁移到修复后的 Workflow，等待自然发布验证。
- 不要为了测试而批量补发失败内容。

## 5. 新 Agent 操作顺序

1. 先读 `README.md`（项目概述）、`PRODUCTION_SAFETY.md`（生产安全原则）、`INCIDENT_THREADS_ACCOUNT_BAN_2026-07-15.md`（事故复盘）。
2. 再读本文件确认路径和边界。
3. 改执行代码前读 `C:\jq\AI\Thread OS\Threads-bot system\AGENTS.md`。
4. 查当前系统状态读 `CURRENT_STATUS.md`。
5. 查当前代码状态读 `Threads-bot system\CONTEXT.md`。
6. 查部署、故障和恢复命令读 `Threads-bot system\RUNBOOK.md`。
7. 改内容库规则时读 `D:\Obsidian\Threads os\README.md`、`AGENT_RULES.md`、`CONTENT_SCHEMA.md`、`WORKFLOW.md`。
8. 以最新远程 `main` 和真实平台运行结果为准，不以旧分支或旧聊天记录为准。

## 6. 禁止事项

- 不调用真实 Threads 发布 API（除非 ENV=production + PUBLISH_ENABLED=true + DRY_RUN=false + 用户明确批准）
- 不使用生产账号做链路测试
- 不发布纯数字、test、hello 等无意义内容
- 不恢复已冻结的自动回复系统。
- 不接入 D1。
- 不重新启用固定 Cron 全队列扫描。
- 不把执行代码、运行状态混入内容正文。
- 不把历史快照仓库重新设为生产入口。
- 不自动重发 `published`、`unknown` 或错过时间的任务。
- 不覆盖其他 Agent 尚未解释的本地修改。
- 不把 Token、API Key 或完整认证 Header 写入 Git 和日志。
- 不在新账号授权前触发真实发布。

详细实现、测试和恢复步骤不在本文件重复维护，以执行仓库的 `RUNBOOK.md` 和代码为准。
