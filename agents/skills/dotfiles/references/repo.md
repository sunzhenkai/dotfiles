# 改本仓（开发）

在本仓库提交改动时读本节。使用类操作（装机器、配模块）不在本节。

## 代码布局

| 路径 | 作用 |
|---|---|
| `bin/dotf` | CLI 入口 |
| `src/dotf_cli/` | argparse、dispatch、select、plan/report 输出 |
| `src/dotf_core/` | `registry`（modules.yaml 读取/校验）、`planner`、`config`、备份 |
| `src/dotf_tui/` | 两区 TUI（复用同一 planner） |
| `src/agents/` | skills 编目 / layout / 同步 / instructions / lock |
| `scripts/` | 模块 handler（`scripts/modules/<name>/{install,config,doctor,uninstall}.sh`）、`bootstrap.sh` |
| `agents/` | first-party skill 源（`agents/skills/<id>/`）、全局指令源（`agents/instructions/`）、编目 `skills.yaml`、`skills.lock.yaml`、`runtime.yaml` |
| `modules.yaml` / `profiles.yaml` | 模块与 profile 真相源 |
| `docs/` | 使用文档、`docs/design/` 设计稿、`docs/adr/` 决策 |

`src/` 根级只允许包目录，唯一豁免 `src/ensure_pyyaml.py`（必须在任何包 `__init__` 之前可导入）。

## 常用命令（仓库根执行）

```bash
make registry validate      # modules.yaml 结构 / kind↔install↔handler 对齐 / first-party 双向校验
make test                   # pytest
make lint                   # shellcheck 等
make ci                     # registry validate + test + lint
make skills-lock-update     # 重锁第三方 skill（逐 skill 审计 + revision）
make fmt                    # 格式化
```

## 模块改动

新增/改模块要同时动：`modules.yaml`（字段见文件头注释）、`scripts/modules/<name>/` 下的 handler、必要时 `profiles.yaml`。禁止字段：`script/command/handler/function/exec/run`。

- `kind: binary` 必须有 install handler 与 doctor（`system` / `homebrew` / `fonts` 例外）
- `config` 声明必须显式给 `source/target/strategy/writeable/sensitive/target_mode/preserve/exclude`，`strategy: symlink` 只用于注册表显式声明的只读目标
- `enabled: false` 的模块不参与 `-a` 与 profile，仍可点名执行

## skill 与全局指令改动

| 要改什么 | 改哪 | 生效方式 |
|---|---|---|
| 本仓 CLI 使用说明（本 skill） | `agents/skills/dotfiles/`（`SKILL.md` + `references/`） | `dotf agents -c` |
| 全局 `AGENTS.md` 正文与目标表 | `agents/instructions/AGENTS.md`、`agents/instructions/install.yaml` | `dotf agents -c` |
| 第三方 skill 的版本 | `make skills-lock-update`（不改内容） | `dotf agents -c` |
| 编目增删 skill | `agents/skills.yaml`（group 声明 `type`，成员只写 id） | `dotf agents -c` |

- 安装产物（各 layout 的 skills 目录、`~/.agents/AGENTS.md` 等）不要手改；漂移由 `dotf agents --doctor` 报出。
- first-party skill 的目录集合与编目 id 集合必须双向一致，`make registry validate` 会 fail closed。目录跳过 symlink 与 `openspec-` 前缀。
- `runtime.yaml` 的 `sidecars` 决定哪些子目录随 skill 分发（当前含 `references`、`scripts`）；`patches/`、`evals/`、`experience/`、`evolutions/`、authoring 目录会被剥离，所以不要往 skill 里塞 authoring 产物。
- 本 skill 的源只有一个：`agents/skills/dotfiles/`。不要再在 `.agents/skills/` 下放同名副本——两份真相源会互相漂移。

## 测试与文档同步

- 改 CLI 行为 / 新增命令 / 语义变化：同步 `agents/skills/dotfiles/`（本 skill）与 `docs/Dotfiles.md`、`README.md`。
- 改编目机制 / lock 行为：同步 `docs/design/skill-catalog.md` 与 `CONTEXT.md`。
- 改部署或模块清单：同步 `agents/README.md` 的布局图。
- `tests/test_ci_contract.py` 会断言若干文档句子仍在（防止写回旧语义），改文档时别删这些句子。

## 提交约定

- 提交说明写原因，格式跟随 `git log` 既有风格（如 `agents: 第三方身份改按条目粒度，删除退役兼容层`）。
- 不把 agent 加为 co-author。
- 开源仓库：提交前确认没有密钥、内部主机名、内网 URL。新增公开仓首次 push 前跑全历史扫描。
- 大改动走 OpenSpec（`openspec/`）：proposal → design → tasks → specs delta；`openspec validate <change> --strict` 必须过。
