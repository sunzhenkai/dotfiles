# Skill 编目与安装模型设计（v3，定稿）

**状态**：已实现
**范围**：`agents/skills.yaml` 编目 schema、`dotf agents -c` 全量安装、`dotf skills -i/-r` 手动安装、desired set
**取代**：ADR-0007 的编目表述（overlay / prune 语义仍以其为准）

---

## 1. 目标

1. **一份编目**覆盖全部 skill：个人（一手）skill、第三方 skill（skills.sh 注册表 + GitHub 直装）。
2. 两种安装模式：**全量安装**（`dotf agents -c` 自动装编目内全部）与**手动安装**（`dotf agents skill apply <id|group>` 受管，或 `dotf skills -i <name>` npx）。
3. **取消 `default` 开关**：编目内即默认全装；不想装就注释掉条目。
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
    skills:                             # 成员安装 id；可为空
      - <skill-id>
```

- 组声明来源属性；成员只写 id，**不可能在组内写错来源**。
- group 名兼作 CLI 展开单位：`dotf skills -i <group>` / `dotf agents skill apply <group>`。
- **没有 `default` 字段**：编目内即自动全量安装。不想装 → 注释掉条目。
- 一手组（`dotfiles`）不声明 `source`/`package`；其来源是 `agents/skills/<id>/`。
- 第三方 `source` 两值：`github`（URL/owner-repo）与 `registry`（skills.sh 名）。

### 当前编目

| group | type | source | package | 成员数 |
|---|---|---|---|---|
| `dotfiles` | first-party | — | — | 19 |
| `mattpocock` | third-party | github | `mattpocock/skills` | 12 |
| `ui-templates` | third-party | github | `sunzhenkai/ui-templates-skill` | 3 |
| `taste`（注释掉） | third-party | github | `Leonxlnx/taste-skill` | 0 |

- `ui-template-design` 在编目内 → 会默认安装（其 lock 条目已补，钉在 `446922a`）。
- `taste-skill` 组整体注释 → 不自动装、不可经 overlay / `agents apply` 引用；其 lock 条目保留。`dotf skills -i taste-skill` 会把它当普通名字透传给 npx。

## 4. 核心决策

### D1. 组内声明来源，取消 default

- 来源属性提升到 group 级，成员只写 id。
- 编目内 = 要装。"不装" = 注释掉。
- 收益：新增一手 skill 只需加一行 id + 建目录；默认集不再分散在每条上。

### D2. source 分 `registry` 与 `github`

- `github`：`package` 为 URL 或 owner/repo；进默认集/受管安装必须被 lock 固定。
- `registry`：`package` 为 skills.sh 名；同样必须先落 lock 才能进默认集或受管安装。
- 纯 npx 直装（不落 lock）只存在于 `dotf skills -i` 通道。

### D3. 全量安装 vs 手动安装

| | 全量安装 | 手动安装 |
|---|---|---|
| 入口 | `dotf agents -c` | `dotf agents skill apply <id\|group>` / `dotf skills -i <...>` |
| 依据 | 编目内全部 | 显式指定 + 写 overlay |
| 第三方前提 | 必须 lock | 受管路必须 lock；npx 路不要求 |
| 落 overlay | 否 | **是**（否则下次 sync prune） |
| prune | 是（stale 且未漂） | remove 时是 |

注：取消 `default` 后没有"默认不装但可手动装"的编目状态；要手动装就必须在编目内。若想"平时不装、偶尔手动装"，目前不支持（可用 `dotf skills -i` 的 npx 通道绕过受管模型）。

### D4. 名字解析优先级

`dotf skills -i/-r <name>` 与 `dotf agents skill apply/remove <name>`：

1. **group 名** → 展开成员（`skills -i` 要求同组同 package，否则要求逐条）
2. **skill id** → 单个
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

## 6. 对代码的影响

| 模块 | 变更 |
|---|---|
| `src/agents/skills_catalog.py` | schema v3：group 声明 + 成员平铺；无 default |
| `src/agents/defaults.py` | `catalog_skill_ids` 取代 `selected_default_ids`；lock 校验用组 type |
| `src/agents/desired_set.py` | Desired Set = 编目全部 ∪ overlay 启用 − 停用 |
| `src/agents/skills_map.py` | 解析读 group；`--expand-group` 供受管路展开 |
| `src/dotf_core/overlays.py` | 编目 id 从 group 成员收集 |
| `bin/dotf` | `agents skill apply/remove` 支持 group 展开 |
| `agents/skills.yaml` | 重写为 group 结构 |
| 测试 | schema / 解析 / desired-set / fixtures 全部更新 |

## 7. 已实现状态

- 编目重写完成；`taste` 组注释、`ui-template-design` 编目内。
- `dotf skills -i <group>`、`dotf agents skill apply <group>` 组展开可用。
- 全量测试 581 passed。

## 8. 后续可选项（未实现）

- `dotf skills lock <name>`：从上游 fetch 并写 lock + 编目（当前 lock 更新仍是手改/脚本）。
- registry 来源的 lock 获取流程。
