---
id: skills-store
name: skills-store
description: "用 vercel-labs/skills（npx skills）发现、搜索、安装、移除、更新 Agent Skills。用户提及 skills store、技能商店、安装 skill、搜索 skill、npx skills、skills.sh 时使用。安装/移除/更新必须明确指定项目目录或全局。外部 skill 安装前必须做安全审计。"
---

# Skills Store

通过 [vercel-labs/skills](https://github.com/vercel-labs/skills) CLI 管理 Agent Skills。入口：`npx skills`（无需全局安装）。发现目录：https://skills.sh/

## 硬性规则：作用域

**安装、移除、更新前必须确认作用域**。用户未指定时先问清，禁止默认猜测。

| 作用域 | 含义 | 标志 |
|--------|------|------|
| **项目**（当前目录） | 写入当前项目 `./<agent>/skills/`，可随仓库共享 | 不加 `-g`；update 用 `-p` |
| **全局** | 写入用户目录 `~/.../skills/`，跨项目可用 | `-g` / `--global` |

执行前用一句话复述作用域，例如：「将安装到**当前项目**」或「将安装到**全局**」。

非交互环境（CI / 明确指令）加 `-y`，避免卡住。

## 硬性规则：外部 Skill 安全审计

**凡来源非本仓库 `agents/skills/` 的安装与更新，必须先审计，再安装。** 禁止跳过。

| 场景 | 是否审计 |
|------|----------|
| `npx skills add` 远程仓库 / URL | **必须** |
| `npx skills add` 本地路径（非本仓库真相源） | **必须** |
| `npx skills update` | **必须**（对新版本重新审计） |
| 本仓库 `agents/skills/` 经 sync 分发 | 已由仓库维护，无需重复审计 |
| `find` / `list` / `use`（不安装） | 不审计 |

审计脚本（与本 SKILL.md 同目录）：

```bash
# 项目内 skill 自带脚本
SKILL_ROOT="$(dirname "$(readlink -f "${BASH_SOURCE[0]:-$0}")")/..")"
AUDIT="$SKILL_ROOT/scripts/audit-skill.sh"

# 或按安装位置：
# 项目: .cursor/skills/skills-store/scripts/audit-skill.sh
# 全局: ~/.cursor/skills/skills-store/scripts/audit-skill.sh
```

### 安装前工作流（先临时拉取 → 审计 → 再正式安装）

```
1. 确认作用域（项目 / 全局）与 skill 名称
2. 拉取到临时目录（不写入 agent skills 目录）
3. 对目标 skill 目录运行 audit-skill.sh
4. 按审计结论：阻断 / 警告待确认 / 通过
5. 通过或用户确认后，执行 npx skills add
6. 删除临时目录，list 核对
```

#### 步骤 2：临时拉取

```bash
AUDIT_DIR="$(mktemp -d /tmp/skills-audit.XXXXXX)"
trap 'rm -rf "$AUDIT_DIR"' EXIT

# owner/repo 或 GitHub URL → 浅克隆
git clone --depth 1 "https://github.com/<owner>/<repo>.git" "$AUDIT_DIR/src"

# 若 source 已是本地目录
# cp -a /path/to/repo "$AUDIT_DIR/src"

# 列出仓库内 skill（辅助定位子目录）
npx skills add <source> --list
```

定位待审目录 `<skill-path>`：

- 单 skill 仓库：通常为 `$AUDIT_DIR/src` 或 `$AUDIT_DIR/src/<skill-name>/`
- 多 skill 仓库：含 `SKILL.md` 的子目录，与 `--list` 输出一致
- 用 `find "$AUDIT_DIR/src" -name SKILL.md` 辅助

#### 步骤 3–4：审计与处置

```bash
bash "$AUDIT" "$AUDIT_DIR/src/<skill-path>"
# 可选 JSON：bash "$AUDIT" "$AUDIT_DIR/src/<skill-path>" --json
```

| 退出码 | 含义 | Agent 行为 |
|--------|------|--------------|
| `0` | 通过 | 继续安装 |
| `1` | 有警告 | **暂停**，向用户展示 findings，**必须**获得明确同意（如「仍要安装」） |
| `2` | 有阻断项 | **禁止安装**；说明原因，建议换来源或自行审查后改本地安装 |

向用户报告审计摘要时包含：规则名、文件、行号、片段；**不要**复读可能含密钥的完整匹配内容。

**`-s '*'` / `--all` 批量安装**：应对**每个** skill 子目录分别审计；任一阻断则整批中止，除非用户明确只要通过项。

用户说「跳过安全检查 / 强制安装」时：仍执行审计并展示结果；阻断项默认仍拒绝，除非用户明确承担风险且仅属警告级——阻断级不可 override。

#### 步骤 5：正式安装

审计通过且 scope 已确认后：

```bash
npx skills add <source> -s <skill-name> -y          # 项目
npx skills add <source> -s <skill-name> -g -a cursor -y   # 全局 + agent
```

## 命令入口

```bash
npx skills <command> [options]
```

不确定版本或参数时先跑：`npx skills --help`。

## 工作流

### 1. 搜索 / 发现

```bash
npx skills find <keyword>
npx skills find <keyword> --owner <github-owner>
npx skills add <owner/repo> --list          # 只列出仓库内技能，不安装
```

向用户展示：名称、来源、简要说明；需要安装时再进入**安全审计 + 安装**流程。

### 2. 安装（add）

**必须：作用域 + 安全审计（见上）。**

```bash
# 项目（当前目录）
npx skills add <source> -s <skill-name> -y
npx skills add <source> -s <skill-name> -a cursor -y

# 全局
npx skills add <source> -s <skill-name> -g -y
npx skills add <source> -s <skill-name> -g -a cursor -y
```

`<source>` 可为：`owner/repo`、GitHub/GitLab URL、git URL、本地路径、仓库内某 skill 的 tree URL。

常用选项：

| 选项 | 说明 |
|------|------|
| `-g` | 全局安装 |
| `-s <name>` | 指定 skill（可多次；`'*'` 表示全部） |
| `-a <agent>` | 目标 agent（如 `cursor`、`claude-code`；`'*'` 表示全部） |
| `-l` | 仅列出，不安装 |
| `-y` | 跳过确认 |
| `--copy` | 复制而非 symlink |
| `--all` | 等价 `--skill '*' --agent '*' -y`（**高风险，须逐 skill 审计**） |

安装后用 `list` 核对。

### 3. 列出已安装

```bash
npx skills list              # 项目
npx skills ls -g             # 全局
npx skills ls -a cursor
npx skills ls --json
```

### 4. 移除（remove）

**必须带作用域。**

```bash
# 项目
npx skills remove <skill-name> -y

# 全局
npx skills remove <skill-name> -g -y

# 指定 agent
npx skills remove <skill-name> -a cursor -y
npx skills remove <skill-name> -g -a cursor -y
```

| 选项 | 说明 |
|------|------|
| `-g` | 从全局移除 |
| `-a <agent>` | 限定 agent（`'*'` = 全部） |
| `-s '*'` / `--all` | 批量清空（慎用，先确认） |
| `-y` | 跳过确认 |

### 5. 更新（update）

**必须带作用域**（`-p` 项目 / `-g` 全局）。**更新前对上游新版本重新走安全审计。**

```bash
npx skills update -p -y                    # 当前项目全部
npx skills update -g -y                    # 全局全部
npx skills update <skill-name> -p -y
npx skills update <skill-name> -g -y
```

不要用无作用域的裸 `npx skills update`（会交互询问）。

### 6. 临时使用（不安装）

```bash
npx skills use <owner/repo>@<skill-name>
npx skills use <owner/repo> --skill <skill-name>
```

只读生成 prompt，不写入 skills 目录；若用户随后要求安装，仍须审计。

## Agent 名速查（常用）

| Agent | `--agent` |
|-------|-----------|
| Cursor | `cursor` |
| Claude Code | `claude-code` |
| Codex | `codex` |
| OpenCode | `opencode` |
| Kiro CLI | `kiro-cli` |
| Pi | `pi` |
| Qoder | `qoder` / `qoder-cn` |
| ZCode | `zcode` |
| CodeBuddy | `codebuddy` |

完整列表见上游 README 或 `npx skills --help`。

## 与本仓库 agents 同步的关系

本仓库共享 skills 真相源在 `agents/skills/`，由 `scripts/agents/sync.sh` / `dotf agents -c` 镜像到各工具。

- **skills-store 安装的第三方 skill**：落在各 agent 的 project/global skills 目录，**不**自动进入 `agents/skills/`。
- 若要把技能纳入本仓库统一真相源：先审计通过，再按需拷贝或改写到 `agents/skills/<id>/`，然后 sync。
- 不要手改由 sync 生成的 `.cursor/skills`、`.claude/skills` 等镜像文件。

## 执行清单

```
- [ ] 已确认操作：find / add / list / remove / update / use
- [ ] add / update 外部来源：已临时拉取并完成 audit-skill.sh
- [ ] 阻断项已拒绝；警告项已获用户明确确认
- [ ] add / remove / update 已明确：项目 或 全局
- [ ] 需要时已指定 -a <agent> 与 -s <skill>
- [ ] 非交互加 -y
- [ ] 临时目录已清理；执行后 list 核对并告知用户路径含义
```

## 示例对话映射

| 用户意图 | 动作 |
|----------|------|
| 「搜 typescript 相关 skill」 | `npx skills find typescript` |
| 「装到当前项目」 | 临时克隆 → 审计 → `npx skills add <src> -s <name> -y` |
| 「全局安装给 cursor」 | 临时克隆 → 审计 → `npx skills add <src> -s <name> -g -a cursor -y` |
| 「删掉全局的 xxx」 | `npx skills remove xxx -g -y` |
| 「更新当前目录的 skills」 | 对新版本审计 → `npx skills update -p -y` |
| 「装哪个？项目还是全局？」未说清 | **先问**，再审计与安装 |
| 审计有 BLOCK | **拒绝安装**，说明规则与位置 |
| 审计仅有 WARN | 展示摘要，等用户确认 |
