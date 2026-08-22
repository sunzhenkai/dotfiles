---
id: service-manager
name: service-manager
description: 项目服务管理：从 Makefile、package.json、docker-compose 等探索服务启动方式，统一执行 list / start / stop / restart / status / logs。按项目隔离缓存与日志；安全停止（进程组优先）；缺 name 默认询问。完成后给出改动范围、影响面与服务访问方式总结。在启动、停止、查看项目服务时使用。
---

# 服务管理

面向用户的输出默认使用简体中文。命令名、路径、代码、状态值与既成术语保持原文，不要逐词硬翻。

管理当前项目的服务生命周期。单一 skill，通过 phase（`list` / `start` / `stop` / `restart` / `status` / `logs`）分派行为，不拆 skill 族。

## 项目根

- **项目根**：从当前工作目录向上找，优先含 `.git` 的目录；否则含 `Makefile` / `package.json` / `docker-compose.yml` / `compose.yaml` / `.service-manager.md` 的最近目录；都找不到则以 cwd 为根，并在输出中说明。
- 只管理该项目根之内的服务；`.service-manager.md` 写在项目根；缓存 key 用**项目根绝对路径**的 md5。
- monorepo 子目录调用时：若用户明确指向子包，以该子包为项目根；否则用仓库根并在 list 中区分各服务 `cwd`。

## 两层信息

令 `<ph>` = `md5(项目根绝对路径)`。

| 层 | 路径 | 用途 | 是否进仓库 |
|----|------|------|------------|
| 运行时缓存 | `~/.cache/service-manager/<ph>.json` | 服务清单、pgid/pid/容器、日志路径 | 否 |
| 项目信息 | `<项目根>/.service-manager.md` | 启动方式、依赖、端口、踩坑 | 是（随项目走） |

日志目录：`~/.cache/service-manager/logs/<ph>/`（**按项目隔离**）。若仍存在旧路径 `logs/<name>.log`（无 `<ph>`），仅作只读回退，新写入一律进 `logs/<ph>/`。缓存与日志不提交 git。

## 信息缓存（加速再次启动）

- **先读缓存**：缓存存在且关键文件 mtime 未变 → 用缓存清单，跳过探索。
- **缓存失效或不存在**：执行 discover，完成后写入缓存。
- 缓存字段：
  - `services[]`：`name`、`command`、`cwd`、`port`、`source`、可选 `compose_file`、`health`
  - `discovered_at`、`source_mtimes`
  - `runs`：`name` → 原生：`pgid`、`pid`、`log`、`started_at`；compose：`container`、`compose_file`、`started_at`（不记 pid）

缓存示例：

```json
{
  "project": "/abs/path/to/project",
  "discovered_at": "2026-08-02T12:00:00Z",
  "source_mtimes": {"Makefile": 1722600000, "package.json": 1722600000, "docker-compose.yml": 1722600000},
  "services": [
    {"name": "api", "command": "make run-api", "cwd": ".", "port": 8080, "source": "Makefile"},
    {"name": "web", "command": "npm run dev", "cwd": "frontend", "port": 3000, "source": "package.json"},
    {"name": "db", "command": "docker compose up -d db", "cwd": ".", "port": 5432, "source": "docker-compose", "compose_file": "docker-compose.yml"}
  ],
  "runs": {
    "api": {"pgid": 12340, "pid": 12345, "log": "~/.cache/service-manager/logs/<ph>/api.log", "started_at": "..."},
    "db": {"container": "project-db-1", "compose_file": "docker-compose.yml", "started_at": "..."}
  }
}
```

## 项目信息文件（`.service-manager.md`）

记录**启动相关的稳定知识**：缓存管「这次怎么起」，此文件管「这个项目怎么起、踩过什么坑」。

### 冲突与覆盖

1. **人工标注优先**：条目或 notes 含「人工」「勿改」等明确标记，或用户本会话指定的 command → 不得覆盖。
2. **经验证优先于未验证**：文件中已成功 start 过并写回的 command/port，优先于缓存里未验证的 discover 结果；冲突时以文件为准并在输出说明。
3. **start/restart 成功后的校正**：仅校正**本轮实际生效**且与文件不一致的 `command`/`cwd`/`port`/前置条件；不删 notes、不改踩坑、不改带人工标记的字段。
4. **discover 补全**：只补缺失服务/字段，不覆盖已有内容。

### 何时读写

1. **任何 phase 开始时**：若文件存在则先读；冲突处理见上。
2. **discover 完成后**：不存在则创建；已存在则补全缺失项。
3. **start / restart 成功后**：按「冲突与覆盖」写回生效信息。
4. **遇到坑时立刻写入**踩坑节；同一问题更新已有条目，不重复堆砌。

### 文件模板

```markdown
# 服务管理 — <项目名或目录名>

## 概览

- 一句话说明项目如何本地跑起来
- 前置：运行时 / 包管理器 / 必需服务（如 Postgres、Redis）

## 服务

### <name>

- **command**: `...`
- **cwd**: `.` 或子目录
- **port**: 8080（未知则写「待确认」）
- **source**: Makefile / package.json / docker-compose / ...
- **notes**: 环境变量、需先 `cp .env.example .env` 等；开发/测试服务注明 bind（如 `0.0.0.0`）与是否热更新

## 踩坑

- YYYY-MM-DD：现象 → 原因 → 解决/绕过
```

### 写入原则

- 只写与**启动/停止/依赖/端口/环境**相关的信息；不写业务逻辑、密钥明文。
- 不要把 pid、pgid、临时日志路径写进此文件。
- 用户若明确要求不提交该文件，提醒可加入 `.gitignore`，但仍在本地维护。

## 开发/测试启动约定

适用于本地 **开发 / 测试** 原生服务（`source` 为 Makefile / package.json / 语言入口等，或 notes 标明 dev/test）。**不**强制改写：人工标注或用户本会话指定的 command、生产向无 watch 的 `start`/`serve`（且无热更新候选时）、compose 依赖类服务（db/redis 等）。

### 优先热更新方式

discover 与选定 `command` 时，同一服务有多候选则按优先级：

1. 显式 watch/reload：脚本或 target 名为 `dev`、`watch`、`serve:dev`，或命令含 `--reload` / `nodemon` / `air` / `watchexec` / `cargo watch` 等。
2. 框架默认开发入口：如 `npm run dev`、`vite`、`uvicorn --reload`、带 debug/reload 的语言服务器。
3. 仅当无热更新候选时，才用普通 `start`/`serve`/`preview`，并在输出说明「无热更新入口」。

不要把「先 `build` 再静态 `preview`」当作首选开发启动，除非用户指定或仅此可起。

### 绑定 0.0.0.0

start / restart 开发/测试原生服务时，监听地址应为 **`0.0.0.0`**（全网卡），不要默认只绑 `127.0.0.1`。

1. 先看 command / notes / 环境是否已宽绑定（已含 `0.0.0.0`、`--host 0.0.0.0`、`HOST=0.0.0.0` 等）→ 不再追加。
2. 若仍只绑本机或未指定 host，按栈用**可逆、常见**方式补绑定（优先环境变量，其次该工具官方 host 参数），且不得关掉热更新：

| 栈 / 线索 | 优先补法（示例） |
|-----------|------------------|
| Vite / webpack-dev-server | `--host 0.0.0.0` 或 `HOST=0.0.0.0` |
| Next.js | `-H 0.0.0.0` |
| uvicorn / gunicorn | `--host 0.0.0.0` |
| Flask | `--host 0.0.0.0` |
| Django `runserver` | `0.0.0.0:<port>` |
| 读取 `HOST` 的 Node 脚本 | `HOST=0.0.0.0` |

3. 无法安全推断补法 → 仍用原 command 启动，在输出与踩坑注明「可能仅本机可达」，并询问期望的 host 参数；不要臆造少见 flag。
4. 成功后按冲突规则，可将实际生效的 bind（`0.0.0.0`）与「热更新：是/否」写入该服务 notes。

## 探索启动方式（discover）

在项目根及明显子目录（如 `frontend/`、`server/`、各 package）**合并多源**结果，不要因已有 Makefile 就跳过 package.json / compose。

扫描顺序（后源可追加服务；同名服务保留更具体者：子目录 package 脚本 > 根 Makefile 泛化 target，并在输出说明）：

1. **先读** `.service-manager.md`（若存在）。
2. **Makefile** / **Justfile** / **Taskfile.yml**：关注 `run`、`start`、`dev`、`serve`、`up`、`server`、`watch` 类任务；读内容确认实际命令；同服务多候选时按「优先热更新方式」选取。
3. **package.json**（含 workspace 子包）：`scripts` 中的 `dev`、`watch`、`start`、`serve`、`preview`；注意 pnpm/npm/yarn；同包多脚本时优先 `dev`/`watch` 等热更新入口。
4. **docker-compose.yml / compose.yaml**（及 `-f` 常见覆盖文件）：服务名即单元；记录 `compose_file` 与 compose 所在 `cwd`；区分 `docker compose` 与 `docker-compose`。
5. **其他线索**（补充，非「前几项全空才看」）：`pyproject.toml` / `manage.py` / `app.py`、`go.mod`+`cmd/`、`Cargo.toml`、`Procfile`、`mise.toml` tasks、README 启动段落。
6. 推断端口；推不出留空，start 后从日志或 `ss -tlnp` 补。
7. 结束 → 更新缓存，并同步/创建 `.service-manager.md`。

无法确定任何启动方式时，列出线索并问用户，不要瞎猜命令。

## 身份匹配（原生进程）

判断缓存中的 pid/pgid 是否仍是本服务时，按下列**可执行**规则（任一足够则匹配；均失败则视为不匹配）：

1. pid 仍存在（`kill -0`），且其 **pgid** 等于缓存 `runs.<name>.pgid`（若有）。
2. 否则：`ps -p <pid> -o args=` 的命令行包含 command 中的**关键可执行名或脚本名**（如 `node`、`uvicorn`、`make`、包名），而非要求整串全等。
3. `npm`/`pnpm`/`yarn`/`make` 启动的，允许实际进程为子进程（`node`/`python` 等）；此时以 **pgid 或进程树属于缓存 pgid** 为准。

不匹配 → 不 kill，列出候选并问用户。

## 运行状态判定

优先级（高 → 低）：

1. **compose**：`docker compose ps` 为 running → running。
2. **缓存 pgid/pid 匹配且进程存活** → running（即使端口尚未监听，标 `starting` 若未满健康等待窗）。
3. **端口已被本服务身份占用** → running。
4. **仅端口被未知进程占用** → 标 `port_busy`，不要当成已由本 skill 启动；start 前先问用户。
5. 否则 → stopped。

## 阶段

用户消息中的第一个词（或语义）决定 phase；缺省为 `list`。

### list

- 读 `.service-manager.md`（若有）与缓存，或 discover；表格：name、source、command、port、运行状态。
- 缓存命中时说明「来自缓存」；源文件 mtime 变了则先重新 discover。

### start `<name>`

**缺 name 时**：

- 仅 **1** 个已知服务 → 可直接起该服务并说明。
- 多个服务 → **默认询问**要起哪些；仅当用户明确说「全部 / all」时才全起。
- 全起时按依赖常识排序（db/redis 等先于 app）；无依据则按 list 顺序并声明。

步骤：

1. 查 `.service-manager.md` / 缓存；没有则先 discover。
2. 已在运行（见「运行状态判定」）→ 告知并跳过。
3. **环境**：若 notes/文档要求 `.env`，检查 `<cwd>/.env`（或项目根）；缺且存在 `.env.example` → 先告知并询问是否 `cp`，未经同意不擅自复制；缺依赖运行时则写入踩坑并停下。
4. **开发/测试约定**：若属开发/测试原生服务，按「开发/测试启动约定」确认 command 为热更新优先入口，并在需要时补 `0.0.0.0` 绑定；得到实际执行用的 command（可与缓存原文不同，成功后按冲突规则写回）。
5. 后台启动（原生）——**新进程组**，便于整组停止：
   ```bash
   mkdir -p ~/.cache/service-manager/logs/<ph>
   cd <cwd> && setsid nohup <command> >> ~/.cache/service-manager/logs/<ph>/<name>.log 2>&1 & echo $!
   ```
   记录 `pid`、`pgid`（`ps -p <pid> -o pgid=`）、`log`、`started_at`。
   compose：在 compose 文件所在目录执行 `docker compose -f <compose_file> up -d <name>`（必要时加 project 名）；记 `container` 与 `compose_file`，不记 pid。
6. 写回缓存 `runs`。
7. **就绪验证**（默认 2–5s，慢服务可延长到 ~30s，或看 `.service-manager.md` 的 health/notes）：
   - 进程/容器仍在；
   - 有端口则已监听（开发服务期望绑在 `0.0.0.0` 或全网卡；若实际仅 `127.0.0.1` 且本应宽绑定，记入踩坑）；
   - 若配置了 HTTP health / 日志就绪关键字，一并满足。
   失败 → tail 项目隔离日志，写踩坑。
8. 成功 → 按冲突规则同步 `.service-manager.md`（含实际 bind / 是否热更新，若适用）。

### stop `<name>`

1. **compose**：在对应 cwd 用同一 `compose_file` 执行 `docker compose stop <name>`，清理 `runs`。
2. **原生优先整组停**：有 `runs.<name>.pgid` 且身份匹配 → `kill -- -<pgid>`（向进程组发信号）；5s 未退再对**同组** `kill -9 -- -<pgid>`。
3. 仅有 pid、无 pgid：身份匹配后 `kill <pid>`，再查是否仍有子进程占端口；有则列出候选问用户，**不要**直接 `fuser -k`。
4. **禁止默认** `fuser -k <port>/tcp` / 无差别 `lsof ... | xargs kill`。仅当用户明确授权「按端口杀」且已展示将杀进程的 pid/命令行后才可执行。
5. pid/pgid/容器都对不上 → 不猜杀，列候选请用户确认。
6. 新坑立刻写入 `.service-manager.md`。

### restart `<name>`

`stop` 后 `start`；复用已有命令，不重新 discover（除非 start 失败需再探索）。缺 name 时规则同 start。

### status `[name]`

按「运行状态判定」输出：running / starting / stopped / port_busy，以及 pid/pgid 或 container、端口、启动时长。

### logs `<name>` `[行数]`

- 原生：`tail -n <行数, 默认 50> ~/.cache/service-manager/logs/<ph>/<name>.log`（旧路径仅回退）。
- compose：`docker compose -f <compose_file> logs --tail <行数> <name>`。

## 完成后总结

任一 phase 结束（成功或可报告失败）后，在主输出之后给总结：

1. **改动范围**：触达服务、动作、是否更新缓存或 `.service-manager.md`。只读无写入 →「无运行态变更」。
2. **影响面**：端口占用/释放、前置依赖、对其它服务影响；无则「无」。
3. **服务访问方式**：对 running/starting 给出入口。本机优先 `http://127.0.0.1:<port>`（或文档中的 path/HTTPS）；若已确认监听 `0.0.0.0`，可补充局域网可用 `http://<主机IP>:<port>`；仅绑本机则如实写；未知 →「待确认」；失败 →「不可用」并指日志。

**只读 phase**（`list` / `status` / `logs`）：三项仍要出现，但改动范围用固定短句「无运行态变更」，影响面无则「无」，避免复述整表；访问方式只列已知入口。突变 phase（`start` / `stop` / `restart`）写满具体服务名与端口变化。

## 安全与边界

- 只管理项目根内服务；命令在对应 `cwd` 执行。
- **绝不** kill 无关进程；身份不匹配或仅端口冲突时停下来问用户。
- 不默认按端口强杀；需用户明确授权。
- 需要 sudo / 改 systemd：说明并先征得同意。
- 缓存损坏 → 直接重新 discover。
- `.service-manager.md` 禁止密钥明文；可写「见 `.env` / 某环境变量名」。

---

## Self-evolution

本 Skill 具备经验积累、评估与持续进化能力。目录（均相对本 Skill 根目录）：

```text
agents/skills/service-manager/
├── SKILL.md
├── examples/      # 经过验证的优秀执行案例
├── evals/         # 可验证成功标准
└── experience/    # 真实失败 / 成功 / 规律
```

不要为了自进化而破坏上文已规定的目标、流程、工具用法、输出与约束。没有真实案例时不要编造 `examples/` 条目。

### Examples

执行复杂任务前：检查 `examples/`；有相关案例则优先复用；没有则按上文正常执行。

### Evaluation

任务完成前对照相关 `evals/`（见 `evals/cases.yaml`）。优先确定性 Eval；失败则先修输出再交卷。

### Experience

仅在失败、用户纠正、明显成功、新方法或可复用经验时写入 `experience/`。不记 trivial；不伪造；不写密钥/内部 URL。单次失败 → `failures/`；规律需至少两次证据 → `patterns/`。

### Evolution

仅当 Experience 暴露可复用稳定模式时才改本 Skill。禁止单次失败直接改 `SKILL.md`。

实际更新生产 `SKILL.md` 时：

1. 不要直接覆盖原文；用 Git diff 或等价审计记录保留 version / change / reason / evidence。
2. **若当前仓库对 `agents/skills/` 有 patches/ 审计维护流程（如 pwd-skill-manager），优先走该流程**，不与 `skill-evolver` 混用。
3. 否则若环境有 `skill-evolver`，委托它走候选 patch → 验证 → 晋升。
4. 未展示 Proposal 并获用户确认前，不改生产 Skill。
