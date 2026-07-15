# Thread OS 交付审计报告

> 日期：2026-07-15
> 审计范围：全系统 — 账号、代码、文档、Secrets、测试、生产边界

---

## 一、账号与 Token

| 项目 | 值 |
| --- | --- |
| 主运营账号 | `@jq.sifu` |
| 主账号 User ID | `27382011494786050` |
| 备用账号 | `@qq.sifu` |
| 备用账号 User ID | `27572263929068860` |
| 主账号 Token | 长效，60 天有效，至 **2026-09-13** 到期 |
| GitHub Secrets 指向 | `@jq.sifu` |
| Token 续期提醒 | 已设置 cron 任务，**2026-09-08** 触发 |
| Meta App（脆） | `27729696710050958` |
| Meta 父应用 | `2811300642572137` |

---

## 二、代码审计

### 生产安全守卫 `production_guard.py`

| 规则 | 实现 |
| --- | --- |
| 内容拒绝：空内容 | ✅ |
| 内容拒绝：纯数字 | ✅ |
| 内容拒绝：test / hello / 测试 等 | ✅ |
| 内容拒绝：过短（< 10 字符）| ✅ |
| 内容拒绝：重复内容 | ✅ |
| 内容拒绝：已发布 content_id | ✅ |
| 单日上限 | `MAX_DAILY_POSTS=1` |
| 最小发帖间隔 | `MIN_POST_INTERVAL_MINUTES=360` |
| 连续失败熔断 | `MAX_CONSECUTIVE_FAILURES=1` |
| 连续 unknown 熔断 | `MAX_CONSECUTIVE_UNKNOWN=1` |

### 单一发布入口

```
CLI (_run_publish)
  → ProductionGuardConfig.from_env()
  → pre_publish_check()
  → [dry-run: return 0, no API call]
  → [production: store.create_task() → run_publish()
      → ThreadsApiClient.publish_post()]
```

- `ThreadsApiClient.publish_post()` 是**唯一**真实发布路径
- CLI 懒加载客户端：**dry-run 不需要 Threads 凭证**

### 测试

| 项目 | 值 |
| --- | --- |
| Python 测试总数 | 136 |
| 新增生产守卫测试 | `test_production_guard.py` |
| 全部通过 | ✅ `OK` |

---

## 三、生产开关

| 开关 | 默认值 | 当前值 |
| --- | --- | --- |
| `ENV` | `development` | `development` |
| `PUBLISH_ENABLED` | `false` | `false` |
| `DRY_RUN` | `true` | `true` |

**只有当三个条件同时满足时才允许真实发布：**
```
ENV=production AND PUBLISH_ENABLED=true AND DRY_RUN=false
```

---

## 四、文档交付

| 文件 | 位置 | 状态 |
| --- | --- | --- |
| README.md | 项目根目录 + `thread-os/docs/project/` | ✅ 最新 |
| PRODUCTION_SAFETY.md | 项目根目录 + `thread-os/docs/project/` | ✅ 最新 |
| INCIDENT_THREADS_ACCOUNT_BAN_2026-07-15.md | 项目根目录 + `thread-os/docs/project/` | ✅ 最新 |
| CURRENT_STATUS.md | 项目根目录 + `thread-os/docs/project/` | ✅ 最新 |
| THREADS_SYSTEM_HANDOFF.md | 项目根目录 + `thread-os/docs/project/` | ✅ 最新 |
| AGENTS.md | `thread-os/` | ✅ 已更新安全约束 |
| CONTEXT.md | `thread-os/` | ✅ 已更新事故后基线 |
| RUNBOOK.md | `thread-os/` | ✅ 已增加五阶段恢复流程 |
| AUTOREPLY_FROZEN.md | `thread-os/` | ✅ 已重申冻结 |

---

## 五、仓库状态

### `bnuzjq-ops/thread-os`（执行仓库）

| 项 | 状态 |
| --- | --- |
| 远程 origin | `git@github.com:bnuzjq-ops/thread-os.git` (SSH) |
| 最新 commit | `403df33` — Sync latest project docs |
| 本地 vs 远程 | 同步 |
| 测试数据 | ✅ 已清理 |
| 旧账号状态 | `state/publish_tasks.json` 保留用于审计 |

### `bnuzjq-ops/threads-content-library`（内容仓库）

| 项 | 状态 |
| --- | --- |
| 远程 origin | `git@github.com:bnuzjq-ops/threads-content-library.git` (SSH) |
| 最新 commit | `01196b9` — Add archived Threads history |
| 测试内容 | ✅ 10 个测试文件已删除 |
| 真实内容 | `threads-20260714-bazi-slice-01~05.md` 保留 |
| 历史归档 | `content/threads-history/` 68 篇帖子已存档 |

---

## 六、事故复盘

| 项目 | 结论 |
| --- | --- |
| 封禁原因 | Meta 官方大面积误封（广场可查证） |
| 自动化是否导致 | **否** |
| 申诉失败原因 | Meta 申诉系统问题 |
| 账号当前状态 | ✅ 已恢复，正常 |
| 生产安全边界 | ✅ 已建立（为长期运营而建，非仅针对此次事故） |

---

## 七、冻结项

| 系统 | 状态 |
| --- | --- |
| 自动回复 | 🔴 冻结 |
| reply-monitor schedule | ❌ 无触发器 |
| reply-dispatch repository_dispatch | ❌ 无触发器 |
| DeepSeek 自动回复 | ❌ 不运行 |
| 飞书回复链路 | ❌ 不运行 |
| Cloudflare Reply Worker | ❌ 保留但不主动触发 |

---

## 八、GitHub Secrets（thread-os）

| Secret | 最后更新 |
| --- | --- |
| THREADS_ACCESS_TOKEN | 2026-07-15 07:30 UTC |
| THREADS_USER_ID | 2026-07-15 07:30 UTC |
| CONTENT_REPO_TOKEN | 2026-07-14 |
| FEISHU_APP_ID / SECRET / CHAT_ID / VERIFICATION_TOKEN | 2026-07-11 |
| DEEPSEEK_API_KEY | 2026-07-11 |

---

## 九、敏感配置文件

| 文件 | 状态 |
| --- | --- |
| `Threads 助手平台配置.md` | ✅ 已更新，包含 Meta 父应用、子应用、两个账号、三个 Token |
| `GitHub 令牌总表.md` | ✅ 已更新路径与用途修正 |
| `外部服务配置.md` | ✅ 未变化 |
| `Threads助手CloudflareScheduler配置.md` | ✅ CW 无需 Threads 凭证，不动 |

---

## 十、待用户执行的操作

| 操作 | 说明 |
| --- | --- |
| 确认主账号 | `@jq.sifu`（已设定，如需更改请告知） |
| 首次灰度发布 | 提供一条正式内容，打开 PUBLISH_ENABLED |
| Token 续期 | 2026-09-08 提醒触发后，在 Meta 后台刷新并通知我 |

---

## 十一、健康检查

```text
136 tests: OK
thread-os remote: synced
content-library remote: synced
GitHub Secrets: valid (THREADS_USER_ID, THREADS_ACCESS_TOKEN)
ENV=development, PUBLISH_ENABLED=false, DRY_RUN=true
Auto-reply: FROZEN
```
