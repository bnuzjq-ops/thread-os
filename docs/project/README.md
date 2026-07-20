# Thread OS — Threads 自动化运营系统

> **生产状态：@jq.sifu 主账号真实发布已开启；12 篇“十神暗面”内容从 2026-07-20 21:00 起每日一篇，等待首次自然到点核验。**

## 项目定位

长期、安全、稳定地运营 Threads 账号和内容资产。

技术只是工具。保护生产账号资产，高于完成自动化任务。

## 仓库结构

| 路径 | 角色 |
| --- | --- |
| `C:\jq\AI\Thread OS\Threads-bot system` | 执行仓库（代码、Workflow、状态、测试） |
| `D:\Obsidian\Threads os` | 内容资产主库（原稿、排期、快照、回执） |
| `C:\jq\AI\Thread OS\Threads-publish-feed` | 历史快照仓库（不再作为生产入口） |

## 阅读顺序（新 Agent 必读）

1. [THREADS_SYSTEM_HANDOFF.md](THREADS_SYSTEM_HANDOFF.md) — 系统边界与当前链路
2. [PRODUCTION_SAFETY.md](PRODUCTION_SAFETY.md) — 生产安全原则（最高优先级）
3. [INCIDENT_THREADS_ACCOUNT_BAN_2026-07-15.md](INCIDENT_THREADS_ACCOUNT_BAN_2026-07-15.md) — 事故复盘
4. [CURRENT_STATUS.md](CURRENT_STATUS.md) — 当前系统状态
5. [Threads-bot system/AGENTS.md](Threads-bot%20system/AGENTS.md) — Agent 操作约束
6. [Threads-bot system/RUNBOOK.md](Threads-bot%20system/RUNBOOK.md) — 运行与恢复手册
7. [Threads-bot system/CONTEXT.md](Threads-bot%20system/CONTEXT.md) — 技术上下文与基线

## 核心原则（摘要）

详细规则见 [PRODUCTION_SAFETY.md](PRODUCTION_SAFETY.md)。

1. **默认不生产**：ENV=development、PUBLISH_ENABLED=false、DRY_RUN=true
2. **测试与生产隔离**：生产账号不承担链路测试
3. **内容守卫**：拒绝纯数字、test、hello 等无意义内容
4. **异常立即停止**：unknown 不重试，不自动补发
5. **生产保险丝**：单日上限、最小间隔、连续失败熔断
6. **唯一发布入口**：全仓库只能通过 `ThreadsApiClient.publish_post()` 真实发布

## 当前状态

- 主账号 `@jq.sifu`（User ID `27382011494786050`），长效 Token 60 天有效
- 备用账号 `@qq.sifu`（User ID `27572263929068860`），Token 保留本地
- 事故已确认为 Meta 官方大面积误封，账号已恢复
- 事故复盘完成，生产安全边界已建立（[PRODUCTION_SAFETY.md](PRODUCTION_SAFETY.md)）
- 发布链路技术验证已通过，136 个测试全部通过
- 自动回复系统继续冻结
- ENV=production、PUBLISH_ENABLED=true、DRY_RUN=false，真实发布已开启
- 12 个 Cloudflare Workflow 实例正在等待 2026-07-20 至 2026-07-31 每日 21:00 的发布时间

## 敏感配置索引

- Threads API 配置：`C:\Users\bnuzj\Documents\Jq\敏感信息\Threads 助手平台配置.md`
- 飞书回调桥配置：`C:\Users\bnuzj\Documents\Jq\敏感信息\Threads 助手平台配置.md`
- DeepSeek API 配置：`C:\Users\bnuzj\Documents\Jq\敏感信息\外部服务配置.md`
