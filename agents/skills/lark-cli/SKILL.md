---
id: lark-cli
name: lark-cli
description: "飞书 / Lark CLI 路由器：按意图用 `lark-cli skills read` 按需加载官方 lark-* 正文（嵌在 CLI 二进制里，不要落盘到 ~/.agents/skills）。用于消息、日历、文档、多维表格、任务、邮箱、审批等飞书操作。仅在用户点名 lark-cli / 飞书 CLI，或明确要操作飞书业务时使用；不要预加载全部上游 skill。"
---

# lark-cli（飞书 CLI 路由器）

面向用户的输出默认使用简体中文。命令名、路径、代码、状态值与既成术语保持原文。

本 skill 是**薄路由器**：只负责选 id、再向 CLI 取正文。官方 skill 嵌在 `lark-cli` 二进制里，与 CLI 版本同步，**不要**安装到 `~/.agents/skills` 或各 agent 的 skills 目录。

源：[larksuite/cli/skills](https://github.com/larksuite/cli/tree/main/skills)（仅供对照，运行时以 CLI 内嵌为准）。

## 三道门禁（防上下文膨胀）

1. **门 1 · 收窄触发**：用户点名本 skill /「飞书 CLI」/ `lark-cli`，或明确要操作飞书业务（发消息、查日程、改文档、多维表格等）。闲聊「飞书是什么」不加载。
2. **门 2 · 先路由再读**：对照 [catalog](references/catalog.md) 选定**一个**业务 skill；意图不清时先问，不猜。
3. **门 3 · 按需加载**（用 Shell 跑 CLI，**不要**用 Read 去读 `~/.agents/skills`）：
   - 认证/配置/登录/权限 → 只 `lark-cli skills read lark-shared`
   - 业务操作 → 先 `lark-cli skills read lark-shared`，再 `lark-cli skills read <id>`
   - **禁止**一次读多个业务 skill；上游 `references/` 仅在其正文要求时再 `lark-cli skills read <id>/<path>`
   - 任务结束即弃，不要把整份上游 skill 留在后续推理里

## 加载上游 skill

```bash
command -v lark-cli || { echo "missing lark-cli; run: dotf lark-cli -i"; exit 1; }

# 路由表过时或 id 不确定时，用内嵌清单核对
lark-cli skills list

# 读某个 skill 的 SKILL.md（默认 stdout 为原始 markdown）
lark-cli skills read lark-shared
lark-cli skills read lark-im

# 列出 / 读取其 references（仅在 SKILL.md 要求时）
lark-cli skills list lark-im
lark-cli skills list lark-im/references
lark-cli skills read lark-im/references/<file>
```

CLI 不存在 → `dotf lark-cli -i`（或 `npm install -g @larksuite/cli`）。**禁止**再跑：

- `npx @larksuite/cli@latest install`（会把 20+ 个 skill 写入 `~/.agents/skills`，所有 agent 都会扫到）
- `npx skills add larksuite/cli -g`（同上）

若本机已有 `~/.agents/skills/lark-*`，视为误装：不要 Read 那些目录；需要时让用户删掉，改走上面的 `skills read`。

## 执行流程

1. 过门禁；查 [catalog](references/catalog.md) 选定 skill id。表与 CLI 不一致时以 `lark-cli skills list` 为准。
2. 预检：`command -v lark-cli`；未配置则按 `lark-shared` 做 `config init` / `auth login`（后台跑，提取链接/二维码给用户）。
3. `skills read lark-shared`（业务任务必做）+ 目标 skill；严格按其指引调用 `lark-cli`。
4. 写操作先 `--dry-run`（若命令支持）；默认 `--as user`，除非上游 skill 要求 bot 身份延续。
5. 成功/失败用 CLI JSON 的 `ok` 或退出码判断；缺 scope 时回到 `lark-shared` 补权，不要换 skill 硬试。

## 不做什么

- 不把上游 skill 拷进本仓库、同步树或 `~/.agents/skills`（避免漂移与各 agent 启动期 description 膨胀）
- 不替代官方 skill 正文；路由表过时时以 `lark-cli skills list` / `skills read` 为准
- 不把 App Secret / token 写入对话或仓库
