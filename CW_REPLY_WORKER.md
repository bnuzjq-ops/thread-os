# Cloudflare Worker 回复桥配置

这个文件只记录 `threads-reply-worker` 这条桥的 CW 侧配置。

## 这条链路做什么

- Feishu 把卡片回调打到 `https://jqxblue.cc/feishu/callback`
- Cloudflare Worker 校验 Feishu 签名
- Worker 把动作转成 GitHub `repository_dispatch`
- GitHub 再交给后续的 `reply-action` 流程

## 你在 CW 后台需要填的东西

- Worker 名称：`threads-reply-worker`

## 独立调度器（待切换）

`reply_scheduler_worker.mjs` 是独立的 GitHub monitor 触发器，配置文件为
`wrangler.scheduler.toml`。当前没有启用它的 Cron，因为 `reply-monitor.yml`
仍在运行 GitHub schedule；启用前必须先关闭 GitHub schedule，避免双调度。

切换顺序：

1. 部署 scheduler Worker，但先确认 Cron 未产生运行；
2. 关闭 `.github/workflows/reply-monitor.yml` 的 `schedule`；
3. 启用 scheduler Cron；
4. 验证 5 次自然 Cron 触发的 GitHub `repository_dispatch`；
5. 将证据写入验收表。
- 路由或自定义域名：`jqxblue.cc/feishu/callback`
- 事件转发名：默认 `threads_reply_action`

## 需要重新添加的变量

下面这些是给 CW Worker 用的，不要写进 git：

- `FEISHU_VERIFICATION_TOKEN`
- `GITHUB_PAT`
- `GITHUB_REPO`
- `GITHUB_DISPATCH_EVENT`，可选，默认 `threads_reply_action`

示例：

- `GITHUB_REPO=bnuzjq-ops/thread-os`

## `GITHUB_PAT` 的权限要求

因为这条桥调用的是 GitHub `repository_dispatch`，所以这个 PAT 需要对目标仓库有：

- fine-grained PAT：`Contents: write`
- classic PAT：`repo`

如果仓库选错了，或者权限不够，Worker 会在发 dispatch 时返回失败。

## 不需要放进 CW 的东西

- `App Secret` 不参与这条回调桥的验签
- 如果以后要调用 Feishu 其他接口，再单独评估是否需要它

## 我已经帮你分开的信息

- Feishu 应用的公共信息放在根目录 `FEISHU_BACKEND.md`
- 敏感值放在本机目录 `C:\Users\bnuzj\Documents\Jq\敏感信息\Threads助手飞书配置.md`

## 重要提醒

- 这条桥建议直接挂在 `jqxblue.cc`，不要再额外套一层代理
- 如果你以前的回调一直失败，最值得先怀疑的是：域名路由、签名 token、GitHub repo 名称三项有没有对齐
