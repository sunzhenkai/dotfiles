---
id: skill-upgrader
name: skill-upgrader
description: "以可审计 patch 更新任意已有 Skill，或将其升级为自进化（examples/evals/experience）。用户点名 skill-upgrader、要求改 Skill 正文、或升级为自更新时使用；入口先做模式门禁。不要在从零写 Skill、或用 skill-evolver 按经验进化时自动套用。"
---

# Skill Upgrader

面向用户的输出默认使用简体中文。命令名、路径、代码、状态值与既成术语保持原文，不要逐词硬翻。

本 Skill 是**公用**工具：可对任意含 `SKILL.md` 的目录做可审计更新，或做一次性自进化结构升级。所有生产改动必须先写入目标 Skill 的 `patches/`，禁止先改生产文件、事后补 patch。

## 与相关 Skill 的关系

| Skill | 职责 |
|-------|------|
| **本 skill** | 任意 Skill：模式门禁后，`update`（改正文/配套）或 `self-upgrade`（加 examples/evals/experience）；二者都走 `<skill-dir>/patches/` |
| `pwd-skill-manager` | **本仓库套壳**：只维护 `agents/skills/<name>/`；实现上应委托本 skill 的 `update`（外加本仓库公开性/镜像边界），不另搞一套 patch 语义 |
| `skill-evolver` | 基于多次真实执行：提案 → `evolutions/` 候选 → eval → 晋升生产稿 |

- 用户明确选择 `skill-evolver` 或要求按**执行经验**进化时：停止本流程，交给 `skill-evolver`（用 `evolutions/`，不写本 skill 的 `patches/`）。
- 用户明确选择 `pwd-skill-manager` 且目标在本仓库 `agents/skills/`：可走该套壳；套壳仍应落到与本 skill 相同的 `<skill-dir>/patches/` 协议。
- 本 skill **不**根据经验改目标 Skill 的核心行为（那是 `skill-evolver`）。目标尚未具备自进化目录且用户要自更新时，走 `self-upgrade`。

## 模式门禁（强制）

未判定模式前，不得写 patch、不得改生产文件。

根据用户表述判定 **唯一** 模式：

| 模式 | 何时选用 | 做什么 |
|------|----------|--------|
| `update` | 修改已有行为、流程、门禁、references/scripts、修 bug、澄清规则等，**不**以「变成自进化」为目的 | 对生产内容做最小可审计 patch |
| `self-upgrade` | 明确要把已有 Skill **切换/升级为自更新**（加 examples / evals / experience，并注入自进化指令） | 按布局模板补目录与注入段落；改动仍打包进 patch 再应用 |

判定规则：

1. **只说「改 / 修 / 更新 / 重构 Skill」**且未提自进化 → `update`。
2. **点名自进化 / 自更新 / 加 examples·evals·experience / 升级为可进化** → `self-upgrade`。
3. **两者都像或都不像**：先问一句二选一，不猜。笼统的「优化一下这个 Skill」不算已选定模式。
4. **按真实执行经验进化正文** → 不是本 skill；导向 `skill-evolver`。
5. **从零创建 Skill** → 停止；走写作/安装类流程。

一次会话只处理 **一个** 目标 Skill、**一种** 模式、**一轮** patch。

## 门禁（通用）

1. **仅显式触发**：用户点名本 skill / `{{slash:skill-upgrader}}`，或明确要求更新已有 Skill / 升级为自进化。
2. **必须有目标**：给出 skill 名、id 或含 `SKILL.md` 的目录。未指定先问，不猜。
3. **禁止从零创建**：没有现成 `SKILL.md` 就停止。
4. **禁止伪造历史**：`self-upgrade` 时没有真实成功案例就不要编 examples；没有真实执行就不要写 experience 条目。
5. **先 patch 后应用**：任何生产改动必须先有本轮 `proposal.md` + `change.patch`，校验通过并按风险门禁确认后再 `git apply`。

**不算触发**：安装外部 Skill、根据一次失败直接改正文（无模式门禁）、自动进化。

## 强制前置判断

确定改动前，完整读取目标 `SKILL.md` 及与请求直接相关的配套文件，并明确判断：

1. **意图**：要新增、删除或改变什么行为？模式是否已由门禁锁定？
2. **冲突**：是否与现有 frontmatter、门禁、流程、脚本、测试或其他 Skill 职责冲突？
3. **合理性**：改动是否通用、可执行、可验证？`self-upgrade` 是否真的需要自进化结构？

任一项不明确或存在多种会显著改变结果的解释时，先向用户提出聚焦问题，不写 patch。发现请求不合理或冲突时，说明依据并给出最小替代方案；不得机械执行。

## 公开性与隐私

写入目标 Skill 的内容须可随该 Skill 分发：

- 不写入个人姓名、账号、主机名、绝对家目录、凭据、密钥、内部 URL、公司信息或私有仓库内容。
- 路径使用相对路径或语义占位符（如 `<skill-dir>`、`<skill-name>`）。
- 示例使用虚构、通用数据。
- 机器特例留在本地配置，不进入共享 Skill。

## Patch 目录协议

每轮在**目标 Skill 目录**下创建新目录（不是本 skill 自己的目录，除非目标就是本 skill）：

```text
<skill-dir>/patches/<YYYYMMDD-HHMMSS>-<slug>/
├── proposal.md
├── change.patch
└── result.md
```

- `<slug>`：小写英文、数字和连字符，概括单一改动目的。
- 目录必须全新；不得覆盖、改写或删除历史 patch 目录。
- `change.patch` 为 unified diff；路径相对**包含该 Skill 的 Git 仓库根**，且只触及该 `<skill-dir>/` 下生产内容。
- patch 可增删改 `SKILL.md`、`references/`、`scripts/`、`assets/`、测试及 `self-upgrade` 所需的 `examples/` `evals/` `experience/`，但**不得**修改任何已有 `patches/` 历史记录。
- 字段与模板见 [patch-protocol.md](references/patch-protocol.md)。

定位仓库根：从 `<skill-dir>` 向上找 Git 根。找不到 Git 根则停止并说明无法安全 `git apply`，不要改用直接写文件绕过。

生产稿定位补充：

- 本仓库共享 Skill：`agents/skills/<id>/`。**不要**改 sync 生成的 `~/.agents/skills/` 镜像。
- 其它仓库 / 个人 skill：以含 `SKILL.md` 的目录为准。

---

## 工作流（两模式共用）

复制并勾选：

```text
Progress:
- [ ] 模式门禁（update | self-upgrade | abort→evolver/create）
- [ ] 定位并完整读取现有 SKILL.md
- [ ] 前置判断（意图 / 冲突 / 合理性）
- [ ] 写 proposal.md（尚未改生产文件）
- [ ] 判定风险并准备 change.patch
- [ ] git apply --check
- [ ] 风险门禁确认（medium/high）
- [ ] git apply + 验证
- [ ] 写 result.md
```

### 1. 模式门禁与定位

锁定模式与 `<skill-dir>`。目标不存在或名称不唯一时先询问。

### 2. 提案

先完成前置判断，再写本轮 `proposal.md`。一次 patch 只解决一个内聚问题；`self-upgrade` 可将「补齐三目录 + 注入」视为同一内聚问题，但不要夹带无关正文重写。

### 3. 风险

| 风险 | 典型改动 | 应用门禁 |
|------|----------|----------|
| `low` | 错别字、链接、示例、不改变行为的澄清；幂等补齐空 README/`.gitkeep` | patch 校验通过后可直接应用 |
| `medium` | 工作流、输出契约、多文件行为；标准 `self-upgrade`（追加注入 + 建目录） | 展示摘要与 diff，获得用户明确确认 |
| `high` | 触发条件、权限、副作用、安全门禁、删除能力、大范围重写 | 展示风险与 diff，获得用户明确确认 |

不确定时提高一级。用户已明确批准**具体改动内容**可视为已通过对应门禁；笼统的「优化一下」不算批准中高风险 diff。标准 `self-upgrade` 默认至少 `medium`。

### 4. 先写 patch

创建本轮 patch 目录与 `proposal.md`，再编写 `change.patch`。此时不得编辑目标生产文件。

patch 必须：只含 proposal 声明的改动；上下文足以精确应用；新文件用 `/dev/null`；不含 patch 目录自身、临时文件或同步镜像。

### 5. 校验与门禁

在 Git 仓库根执行：

```bash
git apply --check --recount "<skill-dir>/patches/<patch-id>/change.patch"
```

校验失败时只修 `change.patch`，不得绕过或直接改生产文件。通过后按风险等级执行确认门禁。

### 6. 应用与验证

```bash
git apply --recount "<skill-dir>/patches/<patch-id>/change.patch"
git diff --check -- "<skill-dir>"
```

核对：实际 diff 与 proposal/`change.patch` 一致；`SKILL.md` frontmatter 合法且 `name` 与目录名一致；引用路径存在；无隐私泄露；未改镜像目录或历史 `patches/`。

`self-upgrade` 另跑下方「Final Validation」。`update` 则跑目标 Skill 自带的相关测试或确定性检查（若有）。

### 7. 写结果

写 `result.md`。失败则 `status: failed`，保留证据并停止；修复必须**新** patch 目录。

不要自动 sync、commit 或 push。本仓库目标升级后可提醒 `scripts/agents/sync.sh` / `dotf agents -c`。

---

## 模式：update

最小改动满足意图。保留原目标、流程、工具用法、输出与约束；不扩 scope、不顺手润色、不为「以后方便」塞自进化目录。

若用户其实要自进化结构，切回模式门禁，改走 `self-upgrade`，不要在 `update` 里偷偷加 `examples/` `evals/` `experience/`。

---

## 模式：self-upgrade

最终目标：把静态 `SKILL.md` 升级成能从真实执行积累经验、并以 Eval 驱动改进的 Skill。**升级本身的文件写入也必须经 patch 应用**，不要直接 `mkdir`/写生产文件。

输入：

```text
my-skill/
└── SKILL.md
```

升级后：

```text
my-skill/
├── SKILL.md
├── examples/
├── evals/
├── experience/
└── patches/          # 本轮与后续审计记录（本模式创建的首轮 patch 即在此）
```

目录模板、Eval schema、注入正文见（均只读一层）：

- [layout.md](references/layout.md) — 复制清单
- [evals.md](references/evals.md) — 抽取规则与 schema
- [skill-injection.md](references/skill-injection.md) — 追加到目标 SKILL.md 的原文
- [examples-README.md](references/examples-README.md) / [evals-README.md](references/evals-README.md) / [experience-README.md](references/experience-README.md) / [cases.template.yaml](references/cases.template.yaml) — 复制源
- [patch-protocol.md](references/patch-protocol.md) — 本轮 patch 记录格式

### Preserve the original Skill

完整读取现有 `SKILL.md`（及其声明要读的 `references/` / `scripts/`）。不要为了自进化破坏原有行为；不要重写无关段落。

幂等：若 `examples/` `evals/` `experience/` 已存在，保留已有文件；只补缺失的 README / 空目录 / 注入段落。已有 `evals/cases.yaml` 不覆盖，只追加从原文抽出且尚未覆盖的 case。已有同等「Self-evolution」段落则不要再贴一份。

若三目录与注入均已齐全 → `decision: already-upgraded`，不写无意义空 patch。

### 组装内容（写入 change.patch）

1. **examples/** — 仅 README 与约定；无真实成功案例不编造。
2. **evals/** — `README.md` + `cases.yaml`；从原文抽可验证标准；优先确定性 Eval。
3. **experience/** — README + `failures/` `successes/` `patterns/`（空目录 `.gitkeep`）；不伪造历史。
4. **SKILL.md** — 末尾追加与 [skill-injection.md](references/skill-injection.md) 一致的正文（只替换 `<skill-dir>`）；不改写语气或删减门禁。

细节清单见 [layout.md](references/layout.md)。

### Evolution Criteria（写入目标后的行为约束）

Experience 进入 Skill 正文前须：可复用、有证据、能改善结果、不破坏已有能力、可通过 Eval。一次性特例只留 Experience。

实际改生产正文：若环境有 `skill-evolver`，**委托它**；否则可用本 skill 的 `update` 模式走 `patches/`。禁止单次失败直接改 `SKILL.md`。

---

## Versioning

修改 Skill 时不要直接覆盖原意而不留记录。本 skill 以 `patches/<id>/` 作为审计与版本线索；有 Git 时同时依赖 Git 历史。

## 安全约束

- 不把密钥、内部 URL、公司代码、个人凭据写进 examples / evals / experience / SKILL.md / patches 正文
- 不删除仍在生效的安全/门禁规则（除非 `update` 且用户确认该规则本身有害）
- `evals/cases.yaml` 只写可验证期望，不写攻击步骤、exploit、凭据

## Final Validation（self-upgrade）

```text
[ ] 原始 Skill 能力未丢失
[ ] examples/ 已建立
[ ] evals/ 已建立
[ ] experience/ 已建立
[ ] Eval 能覆盖核心能力
[ ] 没有伪造历史经验
[ ] Skill 知道如何读取 examples
[ ] Skill 知道如何运行/参考 evals
[ ] Skill 知道什么时候记录 experience
[ ] Skill 不会因为单次失败修改自己
[ ] 本轮改动经由 patches/ 应用且 result 已写
```

任一项未完成则补齐或 `failed`，不要声称已升级。

## 交付

```text
skill: <name>
path: <skill-dir>
mode: update | self-upgrade
patch: <patch-id>
risk: low | medium | high
status: proposed | applied | failed | already-upgraded | aborted
change: <一句话>
validation: <通过项或失败原因>
next: <需要确认、sync 提醒、转 skill-evolver，或无>
```
