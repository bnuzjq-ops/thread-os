# Threads 自动化系统 V2

这是一个从零重建的新项目。

目标是把 Threads 自动发布、评论监控、回复审核、外部平台回调和任务状态管理拆成清晰、可验证的两条链路，而不是修补旧仓库。

## 仓库分工

- `C:\jq\AI\Thread OS\Threads-bot system`: 自动化执行仓库
- `C:\jq\OBS\threads-system`: 内容仓库，只存素材、草稿、待发布内容，必要时人工编辑

## 敏感配置索引

- Feishu 回调桥配置：`C:\Users\bnuzj\Documents\Jq\敏感信息\Threads助手飞书配置.md`
- Threads API 配置：`C:\Users\bnuzj\Documents\Jq\敏感信息\Threads助手Threads应用配置.md`
- DeepSeek API 配置：`C:\Users\bnuzj\Documents\Jq\敏感信息\Threads助手DeepSeek配置.md`
- 以后先看这里，再去对应的本机敏感文件，不要把密钥写进 git

## 核心链路

- 发布链路: 内容仓库 -> 执行仓库 -> Threads API -> 状态记录
- 回复链路: 评论监控 -> 草稿生成 -> 飞书审核 -> Worker 回调 -> GitHub dispatch -> 回复执行

## 当前状态

- 已建立 Git 历史
- 已有 Python 核心、单元测试和 Feishu 回调桥源码
- 已接入 DeepSeek 草稿生成入口、GitHub dispatch 执行入口和回复任务状态文件
- 本地 JSON 闭环已通过，仍未完成外部平台配置和首次真实联调

## 下一步

先完成最小项目契约，再补实现：

1. `SPEC.md`
2. `ARCHITECTURE.md`
3. `RUNBOOK.md`
4. 业务代码和测试

## 当前已验证范围

JSON MVP 已有发布和人工审核回复链路的本地测试。运行 `python -m unittest discover -s tests` 可执行当前测试。通过只代表本地 mock 验证，不代表真实 Threads、飞书、DeepSeek、GitHub Actions 或 Worker 链路成功。

发布输入契约是带有 `content_id`、`platform: threads`、`status: ready` frontmatter 和非空正文的 Markdown。执行仓库读取输入，Obsidian 内容仓库保持独立且本轮不修改。

## GitHub Actions 敏感配置位置

以下配置只记录名称和位置，不记录任何 Token 值：

- 仓库：`bnuzjq-ops/thread-os`
- 页面：`Settings` → `Secrets and variables` → `Actions`
- 非敏感变量：`CONTENT_REPO`，值为 `bnuzjq-ops/threads-publish-feed`
- 敏感 Secret：`CONTENT_REPO_TOKEN`，应为仅授权 `bnuzjq-ops/threads-publish-feed` 的 fine-grained Token
- Token 权限：`Contents: Read-only`、`Metadata: Read-only`
- Token 值不得写入本地项目、Markdown、记忆、日志或提交记录
- 如果 Token 被粘贴到聊天或其他公开位置，必须立即撤销并重新生成
