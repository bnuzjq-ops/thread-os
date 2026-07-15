# Agent 操作约束

## 最高优先级：生产安全

**在操作本仓库之前，必须先阅读：**

1. `C:\jq\AI\Thread OS\PRODUCTION_SAFETY.md`
2. `C:\jq\AI\Thread OS\INCIDENT_THREADS_ACCOUNT_BAN_2026-07-15.md`
3. `C:\jq\AI\Thread OS\CURRENT_STATUS.md`

违反生产安全规则的后果是账号资产永久损失。

## 强制约束

任何 Agent：
- 不得自行开启生产发布
- 不得自行修改生产 Secret
- 不得自行重配 Threads API
- 不得自行切换新账号
- 不得自行绕过 dry-run
- 不得自行发布真实测试内容（纯数字、test、hello 等）
- 不得自行恢复自动回复
- 不得把聊天结果视为已完成
- 不得在新账号未授权时触发真实发布

## 基本原则

- 先读背景，再动手
- 先确认链路，再改代码
- 先验证，再扩大范围
- 每次只做最小必要修改
- 默认 development，默认 dry-run，默认不调用真实 Threads API

## 当前仓库边界

- 本仓库是执行仓库，不是内容仓库
- 个人知识主库：`D:\Obsidian`
- 新内容资产主库：`D:\Obsidian\Threads os`
- 发布快照仓库：`C:\jq\AI\Thread OS\Threads-publish-feed`
- 旧自动回复代码保留但已冻结

## 变更要求

- 先更新契约文件，再改业务逻辑
- 任何涉及外部平台、回调、Secret、部署的修改，都要先说明验证方法
- 不要把已验证的旧经验当成当前事实，必须重新确认

## 安全要求

- 不读取、不打印、不提交敏感值
- 不默认复用旧 remote
- 未确认新 GitHub 仓库前，不做第一次 push

## 推荐顺序

1. 文档契约
2. 目录与脚手架
3. 最小业务闭环
4. 测试
5. 验证

## Temporary Artifacts And Logs

- Do not write temporary logs, GitHub Actions download archives, screenshots,
  diagnostic exports, or other runtime artifacts directly into `C:\jq\AI`.
- Use `$env:TEMP`, `C:\jq\AI\_artifacts`, or the current repository's ignored
  `.tmp` directory instead.
- Remove temporary artifacts when the investigation is complete. Retained
  evidence must stay in a task-specific artifact directory, never in the
  `C:\jq\AI` root.
