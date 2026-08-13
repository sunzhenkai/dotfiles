---
id: lark-cli
name: lark-cli
description: "飞书 / Lark CLI 路由器：按意图只加载官方 lark-* skill（已由 @larksuite/cli 安装到 ~/.agents/skills）。用于消息、日历、文档、多维表格、任务、邮箱、审批等飞书操作。仅在用户点名 lark-cli / 飞书 CLI，或明确要操作飞书业务时使用；不要预加载全部上游 skill。"
---

# lark-cli（飞书 CLI 路由器）

面向用户的输出默认使用简体中文。命令名、路径、代码、状态值与既成术语保持原文。

本 skill 是**薄路由器**，不复制上游正文。官方 skill 源：
[larksuite/cli/skills](https://github.com/larksuite/cli/tree/main/skills)，本机通常在 `~/.agents/skills/lark-*`（由 `npx @larksuite/cli@latest install` 安装）。

## 三道门禁（防上下文膨胀）

1. **门 1 · 收窄触发**：用户点名本 skill /「飞书 CLI」/ `lark-cli`，或明确要操作飞书业务（发消息、查日程、改文档、多维表格等）。闲聊「飞书是什么」不加载。
2. **门 2 · 先路由再读**：对照 [catalog](references/catalog.md) 选定**一个**业务 skill；意图不清时先问，不猜。
3. **门 3 · 按需加载**：
   - 认证/配置/登录/权限 → 只 Read `lark-shared`
   - 业务操作 → 先 Read `lark-shared`，再 Read **一个**业务 skill 的 `SKILL.md`
   - **禁止**一次读多个业务 skill；上游 skill 内部的 `references/` 仅在其正文要求时再读
   - 任务结束即弃，不要把整份上游 skill 留在后续推理里

## 解析上游路径

```bash
# 优先
ls ~/.agents/skills/<skill-id>/SKILL.md
# 缺失则安装官方包（会写入 ~/.agents/skills/lark-*）
npx -y @larksuite/cli@latest install
# 或: dotf lark-cli -i
command -v lark-cli && lark-cli auth status
```

用 **Read** 读绝对路径，例如：

- `~/.agents/skills/lark-shared/SKILL.md`
- `~/.agents/skills/lark-im/SKILL.md`

展开 `~` 为实际 HOME。路径不存在 → 先安装，不要臆造命令。

## 执行流程

1. 过门禁；查 [catalog](references/catalog.md) 选定 skill id。
2. 预检：`command -v lark-cli`；未配置则按 `lark-shared` 做 `config init` / `auth login`（后台跑，提取链接/二维码给用户）。
3. Read `lark-shared`（业务任务必做）+ 目标 skill；严格按其指引调用 `lark-cli`。
4. 写操作先 `--dry-run`（若命令支持）；默认 `--as user`，除非上游 skill 要求 bot 身份延续。
5. 成功/失败用 CLI JSON 的 `ok` 或退出码判断；缺 scope 时回到 `lark-shared` 补权，不要换 skill 硬试。

## 不做什么

- 不把 20+ 个上游 skill 拷进本仓库或同步树（避免漂移与上下文爆炸）
- 不替代官方 skill 正文；路由表过时时以 `~/.agents/skills/lark-*/SKILL.md` 的 description 为准
- 不把 App Secret / token 写入对话或仓库
