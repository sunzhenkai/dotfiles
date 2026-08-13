---
id: service-manager
name: service-manager
description: 项目服务管理：从 Makefile、package.json、docker-compose 等探索服务启动方式，统一执行 list / start / stop / restart / status / logs。缓存服务清单与运行信息以加速后续启动；把启动相关信息与踩坑写入项目根 .service-manager.md。在启动、停止、查看项目服务时使用。
---

# 服务管理

面向用户的输出默认使用简体中文。命令名、路径、代码、状态值与既成术语保持原文，不要逐词硬翻。

管理当前项目的服务生命周期。单一 skill，通过 phase（`list` / `start` / `stop` / `restart` / `status` / `logs`）分派行为，不拆 skill 族。

## 两层信息

| 层 | 路径 | 用途 | 是否进仓库 |
|----|------|------|------------|
| 运行时缓存 | `~/.cache/service-manager/<md5(项目绝对路径)>.json` | 服务清单、pid、日志路径，加速再次启动 | 否 |
| 项目信息 | 项目根 `.service-manager.md` | 启动方式、依赖、端口、踩坑，供人与后续 agent 复用 | 是（随项目走） |

日志目录：`~/.cache/service-manager/logs/`。缓存与日志不提交 git。

## 信息缓存（加速再次启动）

- **先读缓存**：缓存存在且关键文件（Makefile、package.json、docker-compose.yml 等）mtime 未变 → 直接用缓存中的服务清单，跳过探索。
- **缓存失效或不存在**：执行探索（见下），完成后写入缓存。
- 缓存记录：`services[]`（name、command、cwd、port、source）、`discovered_at`、`source_mtimes`、`runs`（name → pid、log、started_at）。

缓存示例：

```json
{
  "project": "/abs/path/to/project",
  "discovered_at": "2026-08-02T12:00:00Z",
  "source_mtimes": {"Makefile": 1722600000, "package.json": 1722600000},
  "services": [
    {"name": "api", "command": "make run-api", "cwd": ".", "port": 8080, "source": "Makefile"},
    {"name": "web", "command": "npm run dev", "cwd": "frontend", "port": 3000, "source": "package.json"}
  ],
  "runs": {"api": {"pid": 12345, "log": "~/.cache/service-manager/logs/api.log", "started_at": "..."}}
}
```

## 项目信息文件（`.service-manager.md`）

项目根目录的 `.service-manager.md` 记录**启动相关的稳定知识**，与运行时缓存互补：缓存管「这次怎么起」，此文件管「这个项目怎么起、踩过什么坑」。

### 何时读写

1. **任何 phase 开始时**：若文件存在，先读一遍，优先采用其中的启动命令、依赖、端口与已知坑；与 discover/缓存冲突时以文件中经验证的信息为准，并在输出中说明。
2. **discover 完成后**：若文件不存在则创建；若已存在则补全缺失的服务/字段，不覆盖人工补充或已有踩坑记录。
3. **start / restart 成功后**：把实际生效的 command、cwd、port、前置条件写回对应服务条目。
4. **遇到坑时立刻写入**：启动失败、缺依赖、端口冲突、环境变量缺失、权限问题、错误命令等——一旦确认原因或有效绕过方式，**马上**追加到「踩坑」节，不要等到会话结束。同一问题不重复堆砌，更新已有条目即可。

### 文件模板

新建时使用以下结构（按实际删减，保持简洁）：

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
- **notes**: 环境变量、需先 `cp .env.example .env` 等

## 踩坑

- YYYY-MM-DD：现象 → 原因 → 解决/绕过
```

### 写入原则

- 只写与**启动/停止/依赖/端口/环境**相关的信息；不写业务逻辑、密钥明文。
- 踩坑条目要可操作：后人（或下次 agent）按条目能避开或复现修复。
- 不要把 pid、临时日志路径写进此文件（那些属于缓存）。
- 用户若明确要求不提交该文件，提醒可加入 `.gitignore`，但仍在本地维护。

## 探索启动方式（discover）

按以下顺序扫描项目根（及明显子目录如 `frontend/`、`server/`），提取可启动的服务：

1. **先读** `.service-manager.md`（若存在），作为已知线索。
2. **Makefile**：`grep -E '^[a-zA-Z0-9_-]+:' Makefile`，关注 `run`、`start`、`dev`、`serve`、`up`、`server` 类 target；读 target 内容确认实际命令。
3. **package.json**：读 `scripts`，关注 `dev`、`start`、`serve`、`preview`。
4. **docker-compose.yml / compose.yaml**：服务名即单元，`docker compose up -d <name>` 启动；注意 `docker compose` 与 `docker-compose` 两种命令。
5. **其他线索**（仅前几个都没有时）：`pyproject.toml`/`manage.py`/`app.py`（Python）、`go.mod` + `cmd/`（Go）、`Cargo.toml`（Rust）、`Procfile`、README 中的启动段落。
6. 从命令、配置或文档推断端口；推不出就留空，start 后从日志或 `ss -tlnp` 补。
7. discover 结束 → 更新缓存，并按上一节同步/创建 `.service-manager.md`。

无法确定任何启动方式时，列出看到的线索并问用户，不要瞎猜命令。

## 阶段

用户消息中的第一个词（或语义）决定 phase；缺省为 `list`。

### list

- 读 `.service-manager.md`（若有）与缓存，或执行 discover；输出表格：name、source、command、port、运行状态（见 status 判定）。
- 缓存命中时说明「来自缓存」；发现源文件已变更时先重新 discover。

### start `<name>`（缺 name 时启动全部或问用户）

1. 查 `.service-manager.md` / 缓存拿 command/cwd；没有则先 discover。
2. 已在运行（status 判定为活）→ 告知并跳过，不重复起。
3. 后台启动并落日志：
   ```bash
   cd <cwd> && nohup <command> >> ~/.cache/service-manager/logs/<name>.log 2>&1 & echo $!
   ```
   docker compose 类用 `up -d`，不记 pid 记容器名。
4. 把 pid、log、started_at 写回缓存 `runs`。
5. 等 2–5 秒，验证进程仍在且（有端口时）端口已监听；失败则 tail 日志给用户看错误，**并把原因/绕过写入 `.service-manager.md` 踩坑节**。
6. 成功则把生效的启动信息同步进 `.service-manager.md`（缺则补、旧则校正）。

### stop `<name>`

1. 优先用缓存 `runs.<name>.pid`：**先校验该 pid 的命令行与本服务 command 匹配**（`ps -p <pid> -o args=`），匹配才 `kill`，5 秒未退再 `kill -9`。
2. pid 失效但知道端口：`fuser -k <port>/tcp` 或 `lsof -ti :<port> | xargs kill`，杀前同样校验进程身份。
3. docker compose：`docker compose stop <name>`。
4. 清理缓存 `runs.<name>`。
5. pid、端口都对不上 → 不猜杀，列出候选进程让用户确认。
6. 若 stop 过程发现新坑（如杀不死、端口被别的进程占用），立刻写入 `.service-manager.md`。

### restart `<name>`

`stop` 后 `start`，复用缓存 / `.service-manager.md` 中的命令，不重新 discover（除非启动失败需要重新探索）。

### status `[name]`

- 缓存有 pid：`kill -0 <pid>` 且命令行匹配 → running。
- 有端口：`ss -tln` 查监听。
- docker compose：`docker compose ps`。
- 输出每个服务 running/stopped + pid + 端口 + 启动时长。

### logs `<name>` `[行数]`

`tail -n <行数, 默认 50> ~/.cache/service-manager/logs/<name>.log`；docker compose 用 `docker compose logs --tail`。

## 安全与边界

- 只管理工作目录内项目的服务；命令一律在对应 `cwd` 下执行。
- **绝不** kill 与本服务无关的进程；身份校验失败时停下来问用户。
- 需要 sudo、会修改系统服务（systemd 等）的请求：说明并先征得同意。
- 缓存文件损坏时直接重新 discover，不要让用户手工修缓存。
- `.service-manager.md` 中禁止写入密钥、token、密码明文；需要时可写「见 `.env` / 某环境变量名」。
