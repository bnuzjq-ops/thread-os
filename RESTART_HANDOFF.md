# Threads Automation Restart Handoff

这份文档是给新上下文直接接手用的。

先看这些文件：

1. [CONTEXT.md](./CONTEXT.md)
2. [README.md](./README.md)
3. [ARCHITECTURE.md](./ARCHITECTURE.md)
4. [RUNBOOK.md](./RUNBOOK.md)
5. [SPEC.md](./SPEC.md)

## 当前状态

- 项目是 Threads 自动化重建，不是旧仓库修补。
- 回复链路已经有 JSON 状态层、TaskStore 抽象和 State API 适配层。
- 发布链路刚补了最小闭环，仍然先用 JSON，不是最终形态。
- 当前任务已经暂停，等待下一次上下文继续。

## 已完成

- `TaskStore` 抽象已建立，`JsonTaskStore` 保持兼容。
- `StateApiTaskStore` 和本地 Cloudflare State Worker 已存在。
- Cloudflare D1 已创建并完成初始迁移。
- 发布链路补齐了：
  - JSON-backed publish queue
  - Threads `publish_post`
  - `publish` CLI
  - `.github/workflows/publish.yml`
- 全量 Python 单测通过。

## 还没做完

- 发布任务还没有迁到 State API / D1。
- 发布链路已有本地 Markdown 输入契约，但还没有接到真正的内容仓库。
- 没有做远程部署、真实 Threads 联调或 Feishu 新联调。

## 下一步建议

1. 先确认发布任务的内容来源。
2. 再把 publish state 从 JSON 迁到 State API / D1。
3. 最后再做远程部署和真实联调。

## 提醒

恢复工作前，务必先读上面列的 md。不要直接从代码开始猜。

## 2026-07-11 JSON 闭环更新

- 当前分支继续使用 JSON，D1 仍延期。
- 发布支持 Markdown source，发布状态和超时处理已明确。
- 回复链路会显式记录 DeepSeek 失败，Threads 不确定结果进入 `unknown`，成功后可回传飞书文本结果。
- reply monitor 和 dispatch 共用回复状态并发组，dispatch 也会回写 JSON；这仍只是 MVP 过渡方案。
- `python -m unittest discover -s tests` 已通过，共 52 个测试。
- 未调用真实外部 API，未部署 Worker，未修改远程 Secret，未修改 Obsidian 内容，未 push。
