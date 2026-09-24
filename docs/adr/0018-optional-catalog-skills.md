# 编目支持 optional 条目：默认不装、可受管按需启用

部分推翻 ADR-0012「没有"是否默认安装"字段」：当时只有两级状态——编目内（默认全装）与注释掉（完全不可受管安装）。实际运行后，`lark-cli`（飞书路由，只有操作飞书时才需要）与 `en-chat`（英语陪练）这类 skill 希望平时不装、不占用各 agent 的 skill 扫描面，但需要时仍走受管通道（overlay `enabled_skills` / `dotf agents skill apply`）一键启用，而不是手动复制目录、也不是走 `dotf skills -i` 的 npx 通道绕过受管模型。

决定：编目组成员在纯 id 字符串之外支持映射形态 `- id: <id>` + `optional: true`。optional 条目**仍在编目内**：属 overlay 合法词汇、可经启用进入 Desired Set、参与 approved/lock/一手覆盖校验；但 Desired Set 公式从「编目全部 ∪ 启用 − 停用」改为「编目非 optional ∪ 启用 − 停用」，默认全量安装（`dotf agents -c`）跳过它们，sync 会把已安装的 optional 条目按 stale prune。`lark-cli`、`en-chat` 首批标记 optional。

保留 ADR-0012 的其余决策：仍无 per-entry `default` 开关（optional 是唯一例外标记，默认行为仍是"装"）；注释掉条目 = 移出编目，照旧既不自动装也不可受管引用。schema 版本不变（v3，成员字符串形态保持合法，映射仅新增 `id`/`optional` 两键且 fail closed 校验）。

> 2026-09-18 修订：成员映射再增加 `aliases`，见 ADR-0023；`optional` 语义不变。
> 2026-09-24 修订：首批 optional 条目中的 `en-chat`（英语陪练）已升级为 `role-chat`（多视角对话），仍标 optional。

随之更新：`src/agents/skills_catalog.py`（成员解析 + `default_ids()`）、`src/agents/desired_set.py`（公式）、`src/dotf_core/overlays.py`（编目 id 收集识别映射成员）、spec `agents-desired-set` 的「Desired Set 组成」、`docs/design/skill-catalog.md`。TUI / doctor 只消费 desired_set，自然把 optional 条目显示为 available，无需另改。

后果：已装这两台 skill 的机器在下次 `dotf agents -c` 时会被 prune（这正是目的）；需要时 `dotf agents skill apply lark-cli` 写 overlay 启用并同次 sync 装回。若未来 optional 形态不够用（如按 profile 区分默认集），再评估是否引入更一般的默认集声明。
