---
name: service-manager
description: 项目服务管理：从 Makefile、package.json、docker-compose 等探索服务启动方式，统一执行 list / start / stop / restart / status / logs。缓存服务清单与运行信息以加速后续启动。在启动、停止、查看项目服务时使用。
---

# Service Manager

管理当前项目的服务生命周期。单一 skill，通过 phase（`list` / `start` / `stop` / `restart` / `status` / `logs`）分派行为，不拆 skill 族。

## 信息缓存（加速再次启动）

缓存文件：`~/.cache/service-manager/<md5(项目绝对路径)>.json`，日志目录：`~/.cache/service-manager/logs/`。不写入仓库、不提交 git。

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

## 探索启动方式（discover）

按以下顺序扫描项目根（及明显子目录如 `frontend/`、`server/`），提取可启动的服务：

1. **Makefile**：`grep -E '^[a-zA-Z0-9_-]+:' Makefile`，关注 `run`、`start`、`dev`、`serve`、`up`、`server` 类 target；读 target 内容确认实际命令。
2. **package.json**：读 `scripts`，关注 `dev`、`start`、`serve`、`preview`。
3. **docker-compose.yml / compose.yaml**：服务名即单元，`docker compose up -d <name>` 启动；注意 `docker compose` 与 `docker-compose` 两种命令。
4. **其他线索**（仅前三个都没有时）：`pyproject.toml`/`manage.py`/`app.py`（Python）、`go.mod` + `cmd/`（Go）、`Cargo.toml`（Rust）、`Procfile`、README 中的启动段落。
5. 从命令、配置或文档推断端口；推不出就留空，start 后从日志或 `ss -tlnp` 补。

无法确定任何启动方式时，列出看到的线索并问用户，不要瞎猜命令。

## Phases

用户消息中的第一个词（或语义）决定 phase；缺省为 `list`。

### list

- 读缓存或执行 discover，输出表格：name、source、command、port、运行状态（见 status 判定）。
- 缓存命中时说明 "from cache"；发现源文件已变更时先重新 discover。

### start `<name>`（缺 name 时启动全部或问用户）

1. 查缓存拿 command/cwd；没有则先 discover。
2. 已在运行（status 判定为活）→ 告知并跳过，不重复起。
3. 后台启动并落日志：
   ```bash
   cd <cwd> && nohup <command> >> ~/.cache/service-manager/logs/<name>.log 2>&1 & echo $!
   ```
   docker compose 类用 `up -d`，不记 pid 记容器名。
4. 把 pid、log、started_at 写回缓存 `runs`。
5. 等 2–5 秒，验证进程仍在且（有端口时）端口已监听；失败则 tail 日志给用户看错误。

### stop `<name>`

1. 优先用缓存 `runs.<name>.pid`：**先校验该 pid 的命令行与本服务 command 匹配**（`ps -p <pid> -o args=`），匹配才 `kill`，5 秒未退再 `kill -9`。
2. pid 失效但知道端口：`fuser -k <port>/tcp` 或 `lsof -ti :<port> | xargs kill`，杀前同样校验进程身份。
3. docker compose：`docker compose stop <name>`。
4. 清理缓存 `runs.<name>`。
5. pid、端口都对不上 → 不猜杀，列出候选进程让用户确认。

### restart `<name>`

`stop` 后 `start`，复用缓存的命令，不重新 discover。

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
