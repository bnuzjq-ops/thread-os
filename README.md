# Threads 自动化系统 V2

这是一个从零重建的新项目。

目标是把 Threads 自动发布、评论监控、回复审核、外部平台回调和任务状态管理拆成清晰、可验证的两条链路，而不是修补旧仓库。

## 仓库分工

- `C:\jq\AI\Thread OS\Threads-bot system`: 自动化执行仓库
- `C:\jq\OBS\threads-system`: 内容仓库，只存素材、草稿、待发布内容，必要时人工编辑

## 核心链路

- 发布链路: 内容仓库 -> 执行仓库 -> Threads API -> 状态记录
- 回复链路: 评论监控 -> 草稿生成 -> 飞书审核 -> Worker 回调 -> GitHub dispatch -> 回复执行

## 当前状态

- 已建立 Git 历史
- 已有 Python 核心、单元测试和 Feishu 回调桥源码
- 仍在补齐 GitHub 端的执行入口和外部平台配置

## 下一步

先完成最小项目契约，再补实现：

1. `SPEC.md`
2. `ARCHITECTURE.md`
3. `RUNBOOK.md`
4. 业务代码和测试
