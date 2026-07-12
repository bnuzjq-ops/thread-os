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

## JSON MVP 验证

```text
python -m unittest discover -s tests
python -m threads_bot_system publish --help
```

`publish --source path/to/post.md` 会创建或复用一个 JSON 发布任务。明确 API 错误进入 `failed`，结果不确定的超时进入 `unknown`，两者都不会被自动重试。回复链路同样遵循此规则，并且发送前必须经过飞书人工确认。

GitHub Actions 当前通过共享并发组和 commit 回写 JSON，这是 MVP 过渡方案，不是最终生产数据库架构；后续仍需迁移到 State API/D1。
