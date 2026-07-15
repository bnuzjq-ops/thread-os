# 当前系统状态

> 更新：2026-07-15
> 状态：@jq.sifu 主账号就绪，长效 Token 60 天有效（至 2026-09-13），CW 调度器正常，等待用户首次灰度发布。

## 整体状态

| 维度 | 状态 | 说明 |
| --- | --- | --- |
| 事故复盘 | ✅ 完成（已修正） | Meta 官方大面积误封，非自动化触发。见 [INCIDENT](INCIDENT_THREADS_ACCOUNT_BAN_2026-07-15.md) |
| 生产安全规则 | ✅ 已建立 | 见 [PRODUCTION_SAFETY.md](PRODUCTION_SAFETY.md)（安全边界为长期运营而建，不是为这次事故补的） |
| 项目主文档 | ✅ 已创建 | 见 [README.md](README.md) |
| 发布链路（技术） | ✅ 已验证 | 两阶段容器 + 发布 + 回执链已验证 |
| 发布链路（生产） | 🔴 关闭 | PUBLISH_ENABLED=false，待用户发起第一次灰度发布 |
| 自动回复系统 | 🔴 冻结 | 不恢复，不部署，不参与当前流程 |
| Threads 主账号 `@jq.sifu` | 🟢 就绪 | 长效 Token（60天），GitHub Secrets 已更新 |
| Threads 备用账号 `@qq.sifu` | 🟡 备用 | Token 保留本地 |
| 现有 Meta App | 🟢 正常 | 同一应用已绑定两个账号 |
| GitHub Actions | 🟢 运行中 | Publish workflow 可用，reply workflow 仅手动 |
| Cloudflare Worker | 🟢 运行中 | Publish scheduler 正常，reply worker 保留 |
| 内容资产主库 | 🟢 正常 | `D:\Obsidian\Threads os`，测试内容已清理 |

## 发布能力

- 动态定时单条发布闭环：✅ 技术验证通过
- 内容库 → 快照 → Cloudflare → GitHub Actions → Threads API：✅ 链验证
- 生产环境真实发布：🔴 关闭（PUBLISH_ENABLED=false）
- 自动回复：🔴 冻结

## 旧账号状态

原 `@jq.sifu` 账号已于 2026-07-15 从 Meta 误封中恢复，现为主账号。旧发布状态保留用于审计：

- `state/publish_tasks.json` — 保留全部旧任务记录（已发布/失败/unknown）
- 旧 post_id 集合（保留在状态文件中，不会被新内容复用）
- 旧 permalink 引用（保留在文档中作为历史证据）
- 旧 Workflow run 日志（GitHub 保留）
- 备用账号 `@qq.sifu` Token 保留本地，用于紧急切换

## 生产安全开关

| 开关 | 当前值 | 说明 |
| --- | --- | --- |
| `ENV` | `development` | 默认开发环境 |
| `PUBLISH_ENABLED` | `false` | 禁止真实发布 |
| `DRY_RUN` | `true` | 默认干运行 |
| `MAX_DAILY_POSTS` | `1` | 新账号初期每日上限 |
| `MIN_POST_INTERVAL_MINUTES` | `360` | 最小发帖间隔 |
| `MAX_CONSECUTIVE_FAILURES` | `1` | 连续失败即暂停 |
| `MAX_CONSECUTIVE_UNKNOWN` | `1` | 连续 unknown 即暂停 |

## 新账号接入阶段

```
[ ] 阶段一：人工养号与稳定性确认（由用户执行）
[ ] 阶段二：API 授权验证（只读，不发布）
[ ] 阶段三：全链 dry-run（不调用真实 Threads Publish API）
[ ] 阶段四：第一次真实灰度发布（一条真实内容，用户确认）
[ ] 阶段五：低频运行（保守限制）
```

当前进度：**阶段一（等待用户创建新账号并完成人工养号）**

## 待用户提供

1. 新 Threads 账号已创建
2. 新账号关联的 Instagram 账号状态正常
3. 新账号可以正常人工发布
4. 新账号已完成初步人工养号
5. 现有 Meta App 是否允许新账号授权（如不允许，是否需要新建 App）
6. 新账号授权后的 THREADS_USER_ID

## 可复用配置

| 配置 | 状态 |
| --- | --- |
| Meta App ID | 🟢 可复用（待确认） |
| Meta App Secret | 🟢 可复用（待确认） |
| GitHub PAT | 🟢 可复用 |
| GitHub 仓库 | 🟢 可复用 |
| Cloudflare Worker | 🟢 可复用 |
| Cloudflare Workflow | 🟢 可复用 |
| 内容库 | 🟢 可复用 |
| 发布代码 | 🟢 可复用 |
| 内容 Schema | 🟢 可复用 |

## 大概率需要更换

| 配置 | 说明 |
| --- | --- |
| `THREADS_USER_ID` | 新账号 ID |
| `THREADS_ACCESS_TOKEN` | 新账号 Access Token |
| 旧账号 profile URL | 文档引用标注为旧账号 |
| 旧测试状态 | 归档，不用于新账号 |

## 禁止自动修改

以下内容只在官方授权流程明确要求时才修改：

- Meta App ID / App Secret
- GitHub PAT
- Cloudflare Worker / Workflow
- GitHub 仓库
- 发布逻辑
