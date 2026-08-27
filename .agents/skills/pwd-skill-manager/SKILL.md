---
id: pwd-skill-manager
name: pwd-skill-manager
description: "通过可审计 patch 管理和更新当前仓库 agents/skills/ 下的共享 Skills。用户要求维护、修改、修复或重构本仓库 Skill 时使用；先判断意图、冲突与合理性，再为每轮更新创建独立 patches 记录，校验后按风险门禁应用。不要用于安装外部 Skill、修改 agent 镜像目录或从真实经验自动进化 Skill。"
---

# PWD Skill Manager

面向用户的输出默认使用简体中文。命令、路径、代码和既成术语保持原文。

本 Skill 是当前工程的项目级维护工具，位于 `.agents/skills/`；它维护公开共享 Skill 真相源 `agents/skills/<skill-name>/`。所有更新必须先形成独立、可审计的 unified diff patch，再应用到目标 Skill；禁止先改生产文件、事后补 patch。

## 边界

- 可修改目标 Skill 整个目录中的生产内容：`SKILL.md`、`references/`、`scripts/`、`assets/` 及其已有测试。
- 不修改 `.agents/skills/` 中除本 Skill 外的项目级 Skill，也不修改 `~/.agents/skills/`、用户主目录等同步生成或安装位置。
- 不负责搜索、安装或升级外部 Skill；此类请求交给相应的 Skill 商店流程。
- 不与 `skill-evolver` 混用。用户选择本 Skill 时，以本 Skill 的 `patches/` 协议为准，不创建 `evolutions/`；用户明确选择 `skill-evolver` 时停止本流程。
- 从零创建公开 Skill 不属于“更新已有 Skill”；创建完成后的每轮修改必须遵守本协议。

## 强制前置判断

确定改动前，读取目标 `SKILL.md` 以及与请求直接相关的配套文件，并明确判断：

1. **意图**：模型要新增、删除或改变什么行为？触发场景和非目标是否明确？
2. **冲突**：是否与现有 frontmatter、门禁、流程、脚本、测试或其他 Skill 的职责冲突？
3. **合理性**：改动是否通用、可执行、可验证，是否值得写进公开共享 Skill？

任一项不明确或存在多种会显著改变结果的解释时，先向用户提出聚焦问题，不写 patch。发现请求不合理或冲突时，直接说明依据并给出最小替代方案；不得机械执行。

## 公开性约束

`agents/skills/` 面向公开复用：

- 不写入个人姓名、账号、主机名、绝对家目录、凭据、密钥、内部 URL、公司信息或私有仓库内容。
- 路径使用仓库相对路径或语义占位符，如 `<repo-root>`、`<skill-name>`。
- 示例使用虚构、通用数据，不复制当前会话中的隐私信息。
- 只加入跨项目或跨环境仍成立的规则；机器特例留在本地配置，不进入共享 Skill。

## Patch 目录协议

每轮只处理一个目标 Skill，并创建一个新目录：

```text
agents/skills/<skill-name>/patches/<YYYYMMDD-HHMMSS>-<slug>/
├── proposal.md
├── change.patch
└── result.md
```

- `<slug>` 使用小写英文、数字和连字符，概括单一改动目的。
- 目录必须全新且独立；不得覆盖、改写或删除历史 patch 目录。
- `change.patch` 是从仓库根应用的 unified diff，路径必须是 `agents/skills/<skill-name>/...`。
- patch 可增删改生产内容，但不得修改任何 `patches/` 历史记录。
- 详细字段和模板见 [references/patch-protocol.md](references/patch-protocol.md)。

## 工作流

### 1. 定位与读取

确认仓库根和目标目录。完整读取目标 `SKILL.md`，按需读取其直接引用、脚本、测试及仓库级规则。目标不存在或名称不唯一时先询问。

### 2. 形成变更提案

先完成“意图 / 冲突 / 合理性”判断，再写 `proposal.md`。一次 patch 只解决一个内聚问题，不夹带格式化、重命名或无关润色。

### 3. 判定风险

| 风险 | 典型改动 | 应用门禁 |
|------|----------|----------|
| `low` | 错别字、链接、示例或不改变行为的澄清 | patch 校验通过后可直接应用 |
| `medium` | 工作流、输出契约、多文件行为或依赖变化 | 展示摘要与 diff，获得用户明确确认 |
| `high` | 触发条件、权限、副作用、安全门禁、删除能力、大范围重写 | 展示风险与 diff，获得用户明确确认 |

不确定时提高一级。用户已明确批准**具体改动内容**可视为已通过对应门禁；笼统的“优化一下”不算批准中高风险 diff。

### 4. 先写 patch

创建本轮目录及 `proposal.md`，然后直接编写 `change.patch`。此时不得编辑目标生产文件。

patch 必须：

- 只包含 proposal 声明的改动；
- 使用足够上下文，能对当前生产文件精确应用；
- 新文件使用 `/dev/null`，删除文件使用对应删除格式；
- 不包含 patch 目录自身、临时文件或同步镜像。

### 5. 校验与门禁

从仓库根执行：

```bash
git apply --check --recount "agents/skills/<skill-name>/patches/<patch-id>/change.patch"
```

校验失败时只修 `change.patch`，不得绕过检查或直接改生产文件。通过后按风险等级执行确认门禁。

### 6. 应用与验证

门禁通过后从仓库根执行：

```bash
git apply --recount "agents/skills/<skill-name>/patches/<patch-id>/change.patch"
git diff --check -- "agents/skills/<skill-name>"
```

随后运行目标 Skill 自带的相关测试或确定性检查，并核对：

- 实际 diff 与 proposal、`change.patch` 一致；
- `SKILL.md` frontmatter 合法，`name` 与目录名一致；
- 引用路径存在，脚本权限和副作用未意外变化；
- 没有隐私信息、无关改动或镜像目录变更。

### 7. 写结果

应用后创建 `result.md`，记录状态、验证和实际偏差。若应用或验证失败，状态写 `failed`，保留证据并停止；修复必须创建新的 patch 目录，不能篡改已应用记录。

不要自动执行 sync、commit 或 push。仅在用户要求时走对应流程。

## 交付格式

```text
skill: <skill-name>
patch: <patch-id>
risk: low | medium | high
status: proposed | applied | failed
change: <一句话>
validation: <通过项或失败原因>
next: <需要确认、sync 提醒或无>
```

