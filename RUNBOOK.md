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
