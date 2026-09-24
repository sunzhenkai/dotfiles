# Skill 编目与安装模型设计（v3，定稿）

**状态**：已实现
**范围**：`agents/skills.yaml` 编目 schema、`dotf agents -c` / `dotf skills -c` 全量安装、`dotf skills -i/-r` 手动安装、desired set
**取代**：ADR-0007 的编目表述（overlay / prune 语义仍以其为准）

---

## 1. 目标

1. **一份编目**覆盖全部 skill：个人（一手）skill、第三方 skill（skills.sh 注册表 + GitHub 直装）。
2. 两种安装模式：**全量安装**（`dotf agents -c` 或 `dotf skills -c` 装编目 Desired Set；后者不含全局 AGENTS.md）与**手动安装**（`dotf agents skill apply <id|group>` 受管，或 `dotf skills -i <name>` npx）。
3. **无 per-entry `default` 开关**：编目内即默认全装；唯一例外是成员可写 `optional: true`——仍在编目内、可经 overlay 按需启用，但不进默认安装。彻底不想装就注释掉条目。
4. group 既是组织维度，也是 CLI 展开单位。
5. 保持不变量：未锁定第三方拒绝、lock 不可变、overlay 只改本机、remove 必须 overlay + prune。

## 2. 术语

见 `CONTEXT.md`：Skill / First-Party Skill / Third-Party Skill / Skill Group / Locked Skill / Desired Set。

## 3. 编目结构

```yaml
version: 3
lock: skills.lock.yaml

groups:
  <group-name>:
    type: first-party | third-party     # 必填
    source: registry | github           # 第三方必填
    package: <url|name>                 # 第三方必填
    skills:                             # 成员安装 id（或映射 `- id` + `optional`）；可为空
      - <skill-id>
      - id: <skill-id>
        optional: true                  # 可选：编目内但默认不装，可经 overlay / apply 启用
        aliases: [ppt]                  # 可选：CLI 短名，解析为正规 id
```

- 组声明来源属性；成员只写 id，**不可能在组内写错来源**。
- group 名兼作 CLI 展开单位：`dotf skills -i <group>` / `dotf agents skill apply <group>`。
- **没有 `default` 字段**：编目内即自动全量安装；`optional: true` 条目是唯一例外（不进默认安装，但可受管启用）。不想保留 → 注释掉条目。
- 一手组（`dotfiles`）不声明 `source`/`package`；其来源是 `agents/skills/<id>/`。
- 第三方 `source` 两值：`github`（URL/owner-repo）与 `registry`（skills.sh 名）。

### 当前编目

| group | type | source | package | 成员数 |
|---|---|---|---|---|
| `dotfiles` | first-party | — | — | 19 |
| `mattpocock` | third-party | github | `mattpocock/skills` | 10（含 2 optional） |
| `ui-templates`（注释掉） | third-party | github | `sunzhenkai/ui-templates-skill` | 0 |
| `ui-skills` | third-party | github | `ibelick/ui-skills` | 1 optional |
| `frontend-slides` | third-party | github | `zarazhangrui/frontend-slides` | 1 optional（别名 `ppt`） |
| `taste`（注释掉） | third-party | github | `Leonxlnx/taste-skill` | 0 |

- `lark-cli` / `role-chat` / `wizard` / `to-questionnaire` / `ui-skills-root` / `frontend-slides` 标 `optional: true` → 默认不装、sync 会 prune；可经 overlay `enabled_skills` 或 `dotf agents skill apply <id|alias>` 按需启用。`frontend-slides` 另有别名 `ppt`。
- `taste` 与 `ui-templates` 组整体注释 → 不自动装、不可经 overlay / `agents apply` 引用；其 lock 条目保留。`dotf skills -i taste-skill` / `dotf skills -i ui-template-apply` 会把它们当普通名字透传给 npx。

## 4. 核心决策

### D1. 组内声明来源，取消 default

- 来源属性提升到 group 级，成员只写 id。
- 编目内 = 默认要装。"不装"分两级：`optional: true` = 默认不装但可受管启用；注释 = 移出编目。
- 收益：新增一手 skill 只需加一行 id + 建目录；默认集不再分散在每条上。

### D2. source 分 `registry` 与 `github`

- `github`：`package` 为 URL 或 owner/repo；进默认集/受管安装必须被 lock 固定。
- `registry`：`package` 为 skills.sh 名；同样必须先落 lock 才能进默认集或受管安装。
- 纯 npx 直装（不落 lock）只存在于 `dotf skills -i` 通道。

### D3. 全量安装 vs 手动安装

| | 全量安装 | 手动安装 |
|---|---|---|
| 入口 | `dotf agents -c` / `dotf skills -c`（仅 skill，不含 AGENTS.md） | `dotf agents skill apply <id\|group>` / `dotf skills -i <...>` |
| 依据 | 编目内非 optional 条目 | 显式指定 + 写 overlay |
| 第三方前提 | 必须 lock | 受管路必须 lock；npx 路不要求 |
| 落 overlay | 否（optional 条目除外：启用须写 overlay） | **是**（否则下次 sync prune） |
| prune | 是（stale 且未漂） | remove 时是 |

注：`optional: true` 条目是"平时不装、偶尔受管装"的编目状态：默认全量安装跳过它们，overlay `enabled_skills` 或 `dotf agents skill apply` 可启用；注释掉的条目才完全不可受管安装（`dotf skills -i` 只当普通名字透传 npx）。

### D4. 安装目标：layout 注册表

Skill 装到哪些目录由 `src/agents/layouts.py` 的 `LAYOUTS` 单一表达，一手 / 第三方 / OpenSpec 三类来源都遍历它：

| layout | 目标 | 渲染 |
|---|---|---|
| `shared` | `~/.agents/skills/<id>/` | `{{slash:x}}` → `/x` |
| `kiro` | `${KIRO_HOME:-~/.kiro}/skills/<id>/` | 同上 + 末尾补 `$ARGUMENTS` |
| `claude` | `~/.claude/skills/<id>/` | 同 shared（Claude Code 自消费 `$ARGUMENTS`） |

owner 前缀由 `(layout, source)` 派生（`agents[:kiro][:claude]-<source>:<id>`），**必须**互不重叠：runtime manifest 是全 layout 共用的一份，`apply_owned_plan` 按 owner 前缀决定保留哪些既有条目。identity 前缀为 `<base>[:kiro][:claude]`。`claude` 拒绝编目 id `synced`（Claude Code 保留目录名）。

### D5. 冲突出口

默认 fail closed。"owned 目标漂移"（内容或 mode）可由 `--on-conflict=backup` 解除：编译期改判为 update，写路径复用 `atomic_write(backup_root=...)`，旧字节留在 `${XDG_STATE_HOME:-~/.local/state}/dotf/backups/<run-id>/<home 相对路径>`。不安全类型、manifest 不可解析、所有权不符、无所有权目标、越界目标，以及所有反向动作，都不受该开关影响。

### D6. 名字解析优先级

`dotf skills -i/-r <name>` 与 `dotf agents skill apply/remove <name>`：

1. **group 名** → 展开成员（`skills -i` 要求同组同 package，否则要求逐条）
2. **skill id 或 alias** → 单个正规 id（别名先收成编目 id）
3. **透传 npx**（仅 `dotf skills -i`）

- group 与 id 同名 → 优先 group，打印提示。
- 一手 id 走 `dotf skills -i` → 拒绝，提示改用 `dotf agents skill apply`。
- 未知 id / 编目外 → fail closed，不进 overlay。

## 5. 不变量（校验，fail closed）

1. `skills` id 全局唯一、非空、不含 `/`。
2. `type` 必须是 `first-party`/`third-party`；第三方必须有 `source`（`registry`/`github`）与 `package`；一手不得声明 `package`/`source`。
3. 一手目录集合 == 编目里 `type: first-party` 的 id 集合（双向）。
4. 编目里每个 third-party id 必须在 lock 覆盖；一手 id 不得在 lock。
5. overlay 只能启用/停用编目内 id。
6. `optional` 只允许写在成员映射上，且必须是布尔；`aliases` 只允许写在成员映射上，且必须是非空 id 列表。optional / alias 条目与其他条目一样参与 1–5 全部校验。别名不得与 skill id、group 名或其他别名冲突。

## 6. 对代码的影响

| 模块 | 变更 |
|---|---|
| `src/agents/skills_catalog.py` | schema v3：group 声明 + 成员平铺（支持 `optional: true` 与 `aliases` 映射）；无 default |
| `src/agents/layouts.py` | 安装目标注册表（shared / kiro / claude）+ owner/identity 前缀派生 |
| `src/agents/defaults.py` | `catalog_skill_ids` 取代 `selected_default_ids`；lock 校验用组 type；遍历 LAYOUTS |
| `src/agents/desired_set.py` | Desired Set = 编目非 optional ∪ overlay 启用 − 停用 |
| `src/agents/desired_ops.py` | apply 按 id 来源补齐（一手目录 / 第三方锁定获取）；逐 layout 失败摘要 |
| `src/agents/managed_runtime.py` | `on_conflict` 策略（block/backup）、`remediated` 操作、保留名守卫 |
| `src/agents/skills_map.py` | 解析读 group；`--expand-group` 供受管路展开 |
| `src/dotf_core/overlays.py` | 编目 id 从 group 成员收集 |
| `bin/dotf` | `agents skill apply/remove` 支持 group 展开；`--on-conflict` |
| `agents/skills.yaml` | 重写为 group 结构 |
| 测试 | schema / 解析 / desired-set / fixtures 全部更新 |

## 7. 已实现状态

- 编目重写完成；`taste` 与 `ui-templates` 组注释。
- `dotf skills -i <group>`、`dotf agents skill apply <group>` 组展开可用。
- 三个 layout（shared / kiro / claude）由同一注册表驱动，见 `docs/adr/0019-*`。
- 全量测试 606 passed。

## 8. 后续可选项

- GitHub 来源 lock 升级：`make skills-lock-update`（`src/agents/lock_update.py`）。按 source 仓升到当前 HEAD，审计通过后写 `agents/skills.lock.yaml`；`-c` 仍只装 lock，不直接跟 HEAD。
- `dotf skills lock <name>` CLI 封装尚未做。
- registry 来源的 lock 获取流程。
