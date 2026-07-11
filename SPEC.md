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

- 旧仓库 `C:\jq\AI\threads-bot os` 只能只读参考
- 内容仓库 `C:\jq\OBS\threads-system` 只负责素材和草稿
- 执行仓库只负责自动化、状态、测试和部署
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

未来内容仓库为 `C:\jq\OBS\threads-system`，与执行仓库保持独立。MVP 输入是一份 Markdown：

```yaml
content_id: stable-content-id
platform: threads
status: ready
```

正文作为 Threads 文本发布。当前不读取或修改 Obsidian 仓库，不支持图片，不选择多篇内容。正式接入前还需确定待发布目录、`publish_at`、只读仓库访问和成功后的内容状态更新。

## 已验证与未验证

- 已在本地验证：JSON 建任务、防重复、claim/send 保护、明确失败、不确定结果、DeepSeek 失败显式记录和 mock 飞书结果通知。
- 尚未验证：真实 Threads、DeepSeek、飞书回调、Cloudflare Worker、远程 GitHub Actions 和生产持久化。
