# 生产安全规则

> 本文档优先级高于所有其他项目文档。
> 任何 Agent、Workflow、代码修改不得违反以下规则。

## 核心原则

系统的真实目标不是把内容发到 Threads，而是**长期、安全、稳定地运营 Threads 账号和内容资产**。

真正需要保护的资产优先级：

1. Threads 账号
2. 账号历史、权重、粉丝和信誉
3. 内容资产
4. 发布记录
5. API Token 和应用配置
6. 自动化代码

代码、Workflow、Cloudflare、GitHub Actions 都是可替换工具。如果为了验证自动化而导致账号被封，系统即使技术上成功，也属于业务失败。

---

## 原则一：默认不生产

所有 Agent 和自动化系统的默认行为必须是：

| 配置项 | 默认值 | 说明 |
| --- | --- | --- |
| `ENV` | `development` | 默认开发环境 |
| `PUBLISH_ENABLED` | `false` | 默认禁止真实发布 |
| `DRY_RUN` | `true` | 默认干运行 |

只有同时满足以下三个条件，才允许调用真实 Threads 发布接口：

```
ENV=production AND PUBLISH_ENABLED=true AND DRY_RUN=false
```

默认行为清单：
- 默认不调用真实 Threads API
- 默认不把生产账号作为测试账号
- 默认异常时停止，而不是继续执行
- 默认禁止自动重试真实发布

只有用户**明确批准**真实生产发布，且生产开关已开启时，才允许调用真实 Threads API。

---

## 原则二：测试与生产隔离

系统至少区分 Development 和 Production 两个环境。有条件时可增加 Sandbox / Test Account。

### Development 允许

- 内容生成
- Schema 校验
- 发布快照导出
- GitHub Workflow
- Cloudflare Workflow
- `repository_dispatch`
- 状态机
- Mock API
- dry-run

### Development 禁止

- 调用真实 Threads 发布接口
- 使用正式账号发布测试内容
- 发布纯数字、test、hello 等无意义内容
- 对生产账号执行高频测试

### Production 只允许

- 真实、正常、有语义的内容
- 明确审核过的内容
- 用户明确允许发布的内容
- 低频和受控发布

---

## 原则三：生产账号不是测试环境

**禁止**在生产账号发布以下内容：

- 纯数字（如 123、1234、12345）
- test、testing
- hello、hi
- "测试发布"
- 重复正文
- 极短无意义内容
- 仅用于验证链路的内容
- 明显机器测试数据

链路测试必须使用：
- dry-run
- mock
- sandbox
- 测试账号
- 不对外发布的本地测试

---

## 原则四：失败默认停止

以下情况**禁止**自动重试真实发布：

- `unknown` 状态
- Threads 请求超时
- 可能已经发布但响应丢失
- 发布成功后状态回写失败
- publish 状态卡在 `publishing`
- 无法确认外部是否已经产生帖子

遇到以上情况：
1. 停止当前执行
2. 标记 `unknown` 或 `publishing_stuck`
3. 产生异常记录
4. 人工确认 Threads 实际状态
5. **不得直接重发**

---

## 原则五：生产发布需要保险丝

系统必须配置以下保险丝：

| 配置项 | 说明 |
| --- | --- |
| `MAX_DAILY_POSTS` | 单日最大发布数 |
| `MIN_POST_INTERVAL_MINUTES` | 最小发帖间隔（分钟） |
| `MAX_CONSECUTIVE_FAILURES` | 连续失败熔断阈值 |
| `MAX_CONSECUTIVE_UNKNOWN` | 连续 unknown 熔断阈值 |

超过阈值后：
- 熔断（tripped）
- 不发布
- 记录原因
- 产生异常通知
- 需用户明确操作恢复

额外保护：
- 纯测试内容拦截
- 重复内容拦截
- 已发布 `content_id` 不得重复使用

---

## 原则六：Agent 边界

任何 Agent **不得**执行以下操作：

- 自行开启生产发布
- 自行修改生产 Secret
- 自行重配 Threads API
- 自行切换新账号
- 自行绕过 dry-run
- 自行发布真实测试内容
- 自行恢复自动回复
- 把聊天结果视为已完成
- 在新账号未授权时触发真实发布

所有规则必须写入主文档和内容库，新 Agent 启动时必须读取。

---

## 环境模式配置

环境变量（GitHub Secrets / Cloudflare Secrets）：

| 变量 | 作用 | 默认值 |
| --- | --- | --- |
| `ENV` | 环境标识 | `development` |
| `PUBLISH_ENABLED` | 生产总开关 | `false` |
| `DRY_RUN` | 干运行模式 | `true` |
| `MAX_DAILY_POSTS` | 单日最大发布数 | `1` |
| `MIN_POST_INTERVAL_MINUTES` | 最小发帖间隔 | `360` |
| `MAX_CONSECUTIVE_FAILURES` | 连续失败熔断 | `1` |
| `MAX_CONSECUTIVE_UNKNOWN` | 连续 unknown 熔断 | `1` |

## 唯一发布入口

全仓库只能通过 `ThreadsApiClient.publish_post()` 执行真实 Threads 发布。

禁止：
- 不同 Workflow 直接写 API
- 不同模块绕过安全检查
- Agent 新增另一条真实发布路径

## 自动回复系统

自动回复系统**继续冻结**。不得恢复：

- reply-monitor schedule
- reply-dispatch repository_dispatch
- 飞书自动回复
- Cloudflare Reply Worker
- DeepSeek 自动回复
- 自动评论扫描
- 真实评论回复

## 新账号接入原则

1. 不能创建后立即接入自动化
2. 先人工养号
3. 先验证 API 授权（只读）
4. 先全链 dry-run
5. 第一次真实发布：一条真实内容，用户确认
6. 初期保守限制：单日最多 1 条，间隔若干小时

详见 [INCIDENT_THREADS_ACCOUNT_BAN_2026-07-15.md](INCIDENT_THREADS_ACCOUNT_BAN_2026-07-15.md) 中的恢复流程。
