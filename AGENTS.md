# Agent 操作约束

## 基本原则

- 先读背景，再动手
- 先确认链路，再改代码
- 先验证，再扩大范围
- 每次只做最小必要修改

## 当前仓库边界

- 本仓库是执行仓库，不是内容仓库
- 个人知识主库：`D:\Obsidian`
- 新内容资产主库：`D:\Obsidian\Work\Content Library`
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
