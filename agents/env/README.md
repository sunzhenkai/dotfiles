# agents/env

Agent **运行环境**真相源（依赖检查、env schema、安全策略、profile）。

已归入统一 agent 域 `agents/`：`skills/` / `commands/` / `vendors/` / `env/`。

## 边界

| 子目录 | 职责 |
|--------|------|
| `agents/skills/`、`agents/commands/` | 提示词与工作流 |
| `agents/vendors/` | 各工具配置模板（provider/model 等） |
| `agents/env/` | CLI/runtime 检查、env 检查、安全边界 |

不要把 skill/command 写进本目录；也不要把 API Key、cookie 提交到仓库。

## 统一入口

```shell
dotf agents -c
dotf agents -d
dotf agents -cd
scripts/modules/agents/sync.sh all
PYTHONPATH=scripts python3 src/agents/doctor.py
```

## 布局

```text
agents/env/
  README.md
  manifest.yaml           # 工具范围、默认 profile、模块启用
  profiles/               # coding | research | full
  env.schema.yaml         # 变量名 / 用途 / 敏感等级（无真实密钥）
  tools.yaml              # CLI/runtime 检查与安装提示
  security.yaml           # 风险等级与敏感扫描规则
  overlay.schema.yaml     # 外置 overlay v1 schema（严格 unknown-key/type 校验）
  overlay.example.yaml    # 安全示例；复制到 XDG 配置目录
```

## Profiles

| Profile | 内容 | 风险 |
|---------|------|------|
| `coding` | 本地 CLI/runtime 检查 | low |
| `research` | coding 检查 + 智谱 provider 密钥检查（默认） | low |
| `full` | 全部 runtime 与 provider 密钥检查 | low |

`dotf agents -c` 默认使用 `research` profile；显式 `--profile` 或外置 overlay 可切换。

## 快速使用

```shell
dotf agents -c
dotf agents skill apply grill-with-docs
dotf agents skill remove grill-with-docs
scripts/modules/agents/sync.sh all --dry-run
PYTHONPATH=scripts python3 src/agents/doctor.py --verbose
```

Skill Desired Set = 一手 catalog ∪ 默认选中第三方 ∪ overlay `enabled_skills` − `disabled_skills`。apply / remove 只写本机 overlay，不改仓库编目或 lock。

## 本机覆盖

```shell
PYTHONPATH=scripts python3 -m dotf_core.overlays init
```

命令只写 `${XDG_CONFIG_HOME:-$HOME/.config}/dotf/overlays/00-local.yaml`。多个 `*.yaml` 按 UTF-8 文件名字节序加载，mapping 递归合并，后文件的 scalar/list 替换前文件；所有文件在合并前后均严格校验。可覆盖默认 profile 与 Skill Desired Set（`enabled_skills` / `disabled_skills`）以及 Codex `local_toml`。未写新键时保持旧默认全量 sync。

旧 `agents/env/local.yaml`、`local-*.yaml`、`local/*.yaml` 与 `agents/vendors/codex/config.local.toml` 仅作为只读迁移输入，读取时告警。显式迁移：

```shell
PYTHONPATH=scripts python3 -m dotf_core.overlays migrate
```

## 安全

- 仓库只存变量**名**与用途说明（见 `env.schema.yaml`）；真实密钥只放环境变量或系统 keychain
- 本机路径只放 XDG external overlay；仓库 local 文件仅为只读迁移输入
- doctor 会扫描明显 secret / 内网 URL，且**永不打印** secret 值
- MiniMax：`MINIMAX_API_KEY`（本仓库 Codex 打**国内** `api.minimaxi.com`）与 Pi 海外 provider `minimax`（`api.minimax.io`）**不是一回事**；国内 key 用 Pi 须走 `minimax-cn` / `MINIMAX_CN_API_KEY`。专题：`repos/codeup/agent-data/knowledge/snippets/minimax-cn-vs-intl.md`
- Kimi（Pi）：`KIMI_API_KEY` → 内置 provider `kimi-coding`；`dotf pi -c` 会写入 `auth.json` 的 `$KIMI_API_KEY` 引用

### Doctor 安全边界

`PYTHONPATH=scripts python3 src/agents/doctor.py` 是唯一受支持的 Agent doctor CLI/renderer；`doctor_impl.py` 仅保留兼容导入，不维护独立检查逻辑。Doctor 与 skills/instructions 同步共用 runtime ownership manifest 与 planner，并以相同 canonical checks 生成 text/JSON。

敏感备份默认保留 **7 天**。版本化策略位于 `agents/env/security.yaml` 的 `sensitive_backups.retention_days`，可在提交并审查该安全配置后覆盖。每个敏感备份目录可放置 `.dotf-backup.json` 元数据（`version: 1`、`sensitive: true`、带时区的 `created_at`）；doctor 只读取该元数据判断过期，不读取或打印备份内容。

skills/instructions runtime sync 通过 managed ownership manifest 只更新 dotf 拥有的文件。unowned、local modification、unexpected symlink 或 malformed target 都是保守的 conflict/fail，用户内容保持不变；多目标写入先 staging 再提交，失败逆序 rollback，`failed-rollback` 时保留 journal 和备份供人工恢复。

`security.yaml` 的 `scan.rule_version` 随每份 tracked secret scan 报告输出，CI 与运维据此判断结果由哪一版规则边界产生。
