# Codex Configuration

此配置用于 [OpenAI Codex](https://developers.openai.com/codex) CLI。**本仓库不声明 LLM provider、模型与密钥**；运行时 provider/模型选择请在本机 overlay（见「projects 本地化」）或 Codex 自身登录流程中完成。

## 配置说明

`dotf codex -c` 安装受管配置：

```shell
dotf codex -c     # 安装/重装 ~/.codex/config.toml
codex             # 使用 ~/.codex/config.toml
```

- `config.toml` - Codex **基础**配置（base），安装时与 XDG overlay `codex.local_toml` 合并生成 `~/.codex/config.toml`（真实文件，非软链）。**不含 `projects`**（信任列表已本地化，见下节）
  - `approval_policy` / `sandbox_mode` - 审批与沙箱策略
  - `[shell_environment_policy]` / `[tui]` - 子进程环境与 TUI 通知

## projects 本地化（信任列表不入库）

本机 Codex 覆盖统一存放在 `${XDG_CONFIG_HOME:-$HOME/.config}/dotf/overlays/*.yaml`。初始化用 `PYTHONPATH=scripts python3 -m dotf_core.overlays init`；若旧仓库 local 文件存在，运行 `PYTHONPATH=scripts python3 -m dotf_core.overlays migrate`，旧文件只读且会触发弃用告警。

Codex 首次信任一个项目时，会自动把 `[projects."<path>"]` 追加进 `~/.codex/config.toml`。这类内容**机器特定且动态变化**，混进仓库会污染 git（跨机器还会串入他人的路径）。因此本仓库采用「base + local 合并」方案：

| 文件 | 是否入库 | 作用 |
| --- | --- | --- |
| `agents/vendors/codex/config.toml` | ✅ 入库 | 稳定共享配置（policy/tui 等），**不含 projects** |
| `${XDG_CONFIG_HOME:-$HOME/.config}/dotf/overlays/*.yaml` 的 `codex.local_toml` | — 仓库外 | 本机 projects 及任意本地覆盖 |
| `~/.codex/config.toml` | — | 安装时由 base + local **合并生成**（普通文件，非软链） |

`dotf codex -c` 用仓库 `config.toml`（base）+ XDG overlay `codex.local_toml`（local）+ 已安装文件里尚未入库的 `[projects]` **重新 merge 生成** `~/.codex/config.toml`。因此：

- 稳定配置始终以仓库 `config.toml` 为单一来源；
- projects 走 XDG overlay `codex.local_toml`（位于仓库外，不污染仓库）；
- 不创建或读取 `.dotf-profile` marker；
- `dotf codex -c` 会从已安装的 `~/.codex/config.toml` **收回** Codex 运行时写入、且 overlay 尚未声明的 `[projects."<path>"]`。因此重装不会再因「受管文件被 Codex 改过」而 `managed-target-modified`。
- 这些运行时信任**不会自动同步**进 XDG overlay——换机或想把某条路径固化为本机来源时，仍需把对应块写入 `codex.local_toml`。overlay 与运行时同路径时，以 overlay 为准。

> 这是 codex 的已知设计缺陷（[openai/codex#14601](https://github.com/openai/codex/issues/14601)、[#3120](https://github.com/openai/codex/issues/3120)），官方暂未支持 `projects` 独立文件，故由本仓库的安装脚本在外部解决。

### 新机初始化

```bash
PYTHONPATH=scripts python3 -m dotf_core.overlays init
# 在 00-local.yaml 的 codex.local_toml 中按需编辑项目路径
dotf codex -c
```

### 新增 / 删除已信任的项目

编辑 `${XDG_CONFIG_HOME:-$HOME/.config}/dotf/overlays/*.yaml` 中的 `codex.local_toml`，增删对应的 `[projects."<path>"]` 块，然后：

```bash
dotf codex -c
```

（XDG overlay 是要固化的 projects 来源；安装时还会收回当前 `~/.codex/config.toml` 里 overlay 尚未声明的运行时信任。同路径冲突以 overlay 为准。）

## 安装

```bash
dotf codex -c
```

或者直接运行：

```bash
bash scripts/lib/dispatch_config.sh codex
```

## 使用

```bash
codex                              # 交互式 TUI
codex exec "review this change"    # 单次执行
```

## 注意事项

- `config.toml` 采用「base + local 合并生成」（非软链），以免 Codex 自动写入的 projects 污染仓库。
- `~/.codex/` 下的其他状态文件（`auth.json`、`history.jsonl` 等）不纳入 dotfiles 管理。
