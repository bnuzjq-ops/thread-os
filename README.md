# Threads 自动化系统 V2

这是一个把 Threads 自动发布、评论监控、人工审核回复、Feishu 回调和 GitHub Actions 串成闭环的执行仓库。

## 仓库分工

- `C:\jq\AI\Thread OS\Threads-bot system`: 执行仓库，放代码、工作流、运行文档
- `C:\jq\OBS\threads-system`: 内容仓库，只存素材、草稿、待发布内容，按需人工编辑

## 敏感配置索引

- Feishu 回调桥配置：`C:\Users\bnuzj\Documents\Jq\敏感信息\Threads助手飞书配置.md`
- Threads API 配置：`C:\Users\bnuzj\Documents\Jq\敏感信息\Threads助手Threads应用配置.md`
- DeepSeek API 配置：`C:\Users\bnuzj\Documents\Jq\敏感信息\Threads助手DeepSeek配置.md`
- 先看这里，再去对应的本机敏感信息文件，不要把密钥写进 git

## 核心链路

- 发布链路：内容仓库 -> 执行仓库 -> Threads API -> 状态记录
- 回复链路：评论监控 -> 草稿生成 -> Feishu 审核 -> Worker 回调 -> GitHub dispatch -> 回复执行

## 当前状态

- Git 历史已建立
- Python 核心、单元测试、Feishu 回调桥、DeepSeek 草稿生成入口、GitHub dispatch 执行入口都已接通
- 本地 JSON 闭环和云端 Actions 闭环都已跑通过
- 现在的重点是：继续用云端和外部平台返回验证，而不是只看本地代码

## 排查优先级

遇到接口、回调、权限、Webhook、secret、token 相关问题时，按这个顺序看：

1. 先看平台文档和接口返回体
2. 再看 secret / token / user id / permissions / callback URL / workflow env
3. 再看 GitHub Actions 的 run 结论、远端 `main`
4. 最后才看代码本身

Feishu 卡片按钮只带 `action + reply_task_id`，它不是“旧仓库代码链接”。如果旧卡片点不开，优先检查当前 state、当前回调配置和当前云端环境。

## 下一步

1. 先看 `SPEC.md`
2. 再看 `ARCHITECTURE.md`
3. 再看 `RUNBOOK.md`
4. 最后才改业务代码
