# 项目规格

## 目标

- 重建一个最小、稳定、可验证的 Threads 自动化系统
- 发布与回复分离
- 低信息评论走 like-only，高价值评论进入人工审核
- 任何自动化结果都必须能追溯、可回滚、可验证

## 非目标

- 不是修复旧仓库
- 不是直接复制旧实现
- 不是把内容仓库和执行仓库混为一体
- 不是完全无人值守的全自动回复系统

## 关键边界

- 个人知识主库是 `D:\Obsidian`
- 新内容事实源是 `D:\Obsidian\Work\Content Library`
- 发布快照仓库是 `C:\jq\AI\Thread OS\Threads-publish-feed`
- 执行仓库只负责自动化、状态、测试和部署
- 旧自动回复系统已冻结，只保留手动恢复入口
- 敏感配置只放环境变量或平台 Secret，不写入 Git

## 验证原则

- 每个链路都要有单点验证
- 每次修改都要能复现成功或失败
- 先验证契约，再扩展功能

## 最小交付顺序

1. 仓库骨架与项目契约
2. 发布链路最小闭环
3. 回复链路最小闭环
4. 状态记录与测试

## 当前内容源契约

内容库与执行仓库保持独立。发布器实际读取发布快照仓库中的 Markdown：

```yaml
content_id: stable-content-id
platform: threads
editorial_status: ready
```

正文作为 Threads 文本发布。Content Library 中 `status: approved` 或 `status: scheduled` 的内容通过导出脚本转换为该快照格式。当前不支持图片，不迁移旧内容。

## 已验证与未验证

- 已在本地验证：JSON 建任务、防重复、claim/send 保护、明确失败、不确定结果、DeepSeek 失败显式记录和 mock 飞书结果通知。
- 尚未验证：真实 Threads、DeepSeek、飞书回调、Cloudflare Worker、远程 GitHub Actions 和生产持久化。
