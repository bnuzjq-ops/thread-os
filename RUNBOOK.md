# 运行手册

## 开工前

1. 先读 `README.md`
2. 再读 `SPEC.md`
3. 再读 `ARCHITECTURE.md`
4. 先确认当前要改的是哪条链路

## 本地验证

- 先看 `git status`
- 再跑单元测试
- 再跑最小云端验证

## 修改原则

- 每次只改一个清晰的点
- 不重构无关文件
- 不把 secret 写进 git
- 不把历史路径当成当前事实

## 外部平台优先级

遇到接口、回调、鉴权、权限、Webhook、secret、token 相关问题时，先按下面顺序排查：

1. 外部平台返回体和错误码
2. secret / token / user id / permissions / callback URL / workflow env
3. GitHub Actions run 和远端 `main`
4. 代码本身

不要先默认是代码 bug。

## 当前需要的运行变量

- `FEISHU_APP_ID`
- `FEISHU_APP_SECRET`
- `FEISHU_CHAT_ID`
- `DEEPSEEK_API_KEY`
- `DEEPSEEK_MODEL`，可选，默认 `deepseek-v4-flash`
- `DEEPSEEK_BASE_URL`，可选，默认 `https://api.deepseek.com`
- `THREADS_ACCESS_TOKEN`
- `THREADS_USER_ID`
- `THREADS_STORE_PATH`，可选，默认 `state/reply_tasks.json`

监控入口会先按 `THREADS_USER_ID` 自动拉取当前用户的 Threads 帖子，再扫每条帖子的回复；`--media-id` 只保留给手动临时指定单帖扫描。监控也会跳过你已经在 Threads 里自己回复过的顶层评论，避免旧帖反复重提。

## Cloudflare Worker 仍然需要的变量

- `FEISHU_VERIFICATION_TOKEN`
- `GITHUB_PAT`
- `GITHUB_REPO`
- `GITHUB_DISPATCH_EVENT`，可选，默认 `threads_reply_action`

## Feishu / GitHub 连接

- Feishu 卡片按钮只带 `send / rewrite / skip / status + reply_task_id`
- Worker 把动作转成 GitHub `repository_dispatch`
- GitHub 再交给后续的 `reply` 流程
- 如果旧卡片有问题，先看当前 state 里还有没有对应 task，再看 worker 和 GitHub 配置

## 失败处理

- 先判断是配置、权限、代码还是外部平台问题
- 不要重复试错同一条路径
- 保留错误输出和复现步骤

## JSON MVP 验证

```text
python -m unittest discover -s tests
python -m threads_bot_system publish --help
```

`publish --source path/to/post.md` 会创建或复用一个 JSON 发布任务。明确 API 错误进入 `failed`，结果不确定的超时进入 `unknown`，两者都不会被自动重试。回复链路同样遵循这条规则，并且发送前必须经过 Feishu 人工确认。

GitHub Actions 现在通过共享变量和 commit 回写 JSON，这只是 MVP 过渡方案，不是最终生产数据仓库架构；后续仍需迁移到 State API / D1。

## Publish feed operations（2026-07-12）

### A 导出到 B

```powershell
python -m threads_bot_system export-content --source "C:\jq\OBS\30-Content\Threads\Ready\<file>.md" --feed-repo "C:\jq\AI\Thread OS\Threads-publish-feed"
```

- 命令只读取显式指定的单个 Ready 文件，不扫描整个 A。
- 默认只生成本地 B 快照；显式增加 `--push` 才提交并推送 B 的 `main`。
- B 已有同一 `content_id` 时默认停止；仅未发布内容可在确认后使用 `--replace`。
- 命令不修改 A、不调用 Threads、不修改 C 的 JSON。

### 本地只读 dry run

```powershell
python -m threads_bot_system publish --feed-dir "C:\jq\AI\Thread OS\Threads-publish-feed\posts\queue" --content-id threads-test-001 --dry-run
python -m threads_bot_system publish --feed-dir "C:\jq\AI\Thread OS\Threads-publish-feed\posts\queue" --scheduled --dry-run
```

`threads-test-001` 没有 `scheduled_time`，第二条命令不得选中它。dry run 不写 JSON，也不初始化 Threads 客户端。

### GitHub 配置

- Repository variable：`CONTENT_REPO`，值为 `bnuzjq-ops/threads-publish-feed`。
- Repository secret：`CONTENT_REPO_TOKEN`，fine-grained PAT 仅授权 B，`Contents: Read-only`、`Metadata: Read-only`。
- 不要把 PAT 写入文件或日志。C 的 checkout 对 B 使用 `persist-credentials: false`。
- 人工运行 `Publish Threads` 时必须填写明确的 `content_id`。
- 定时模式只选择 `editorial_status=ready`、`scheduled_time` 带时区且已到期的内容，一次最多一条。

真实发布前仍需人工确认 B 快照和目标 `content_id`。本轮只完成代码与 dry run，不运行线上 workflow。
