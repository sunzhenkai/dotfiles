---
id: skills-store
name: skills-store
description: "用 vercel-labs/skills（npx skills）发现、搜索、安装、移除、更新 Agent Skills。用户提及 skills store、技能商店、安装 skill、搜索 skill、npx skills、skills.sh 时使用。安装/移除/更新必须明确指定项目目录或全局。"
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

向用户展示：名称、来源、简要说明；需要安装时再进入下一步。

### 2. 安装（add）

**必须带作用域。**

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
| `--all` | 等价 `--skill '*' --agent '*' -y` |

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

**必须带作用域**（`-p` 项目 / `-g` 全局）。

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
- 若要把技能纳入本仓库统一真相源：先用本 skill 发现/试用，再按需拷贝或改写到 `agents/skills/<id>/`，然后 sync。
- 不要手改由 sync 生成的 `.cursor/skills`、`.claude/skills` 等镜像文件。

## 执行清单

```
- [ ] 已确认操作：find / add / list / remove / update / use
- [ ] add / remove / update 已明确：项目 或 全局
- [ ] 需要时已指定 -a <agent> 与 -s <skill>
- [ ] 非交互加 -y
- [ ] 执行后 list 核对结果并告知用户路径含义
```

## 示例对话映射

| 用户意图 | 动作 |
|----------|------|
| 「搜 typescript 相关 skill」 | `npx skills find typescript` |
| 「装到当前项目」 | `npx skills add <src> -s <name> -y` |
| 「全局安装给 cursor」 | `npx skills add <src> -s <name> -g -a cursor -y` |
| 「删掉全局的 xxx」 | `npx skills remove xxx -g -y` |
| 「更新当前目录的 skills」 | `npx skills update -p -y` |
| 「装哪个？项目还是全局？」未说清 | **先问**，再执行 |
