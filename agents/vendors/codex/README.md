# Codex Configuration

此配置用于 [OpenAI Codex](https://developers.openai.com/codex) CLI。默认直连 **MiniMax**（国内站 `api.minimaxi.com`，模型 `MiniMax-M3`）；**无需 OpenAI 账号登录**。密钥一律走环境变量（senv `ai` 组），配置文件不含密钥。

## 切换 provider

`dotf codex -f/--profile` 会把选中的 provider 写进 `~/.codex/config.toml` 作为默认，同时安装全部 profile 文件，因此也可以用 `codex --profile <name>` 单次覆盖。TUI 里 `/model`（或 `codex exec -m <slug>`）按当前 catalog 切模型。

```shell
dotf codex -c                    # 按上次选择（或默认 MiniMax）重装配置
dotf codex -f                    # 列出可用 provider
dotf codex -f kimi               # 切换默认 provider（隐含 -c）
dotf codex -c --profile zhipu    # 同上；bigmodel 是 zhipu 的别名
dotf codex -f scnet
dotf codex -f nativex
dotf codex -f minimax            # 切回默认

codex                            # 使用当前默认 provider
codex --profile scnet            # 仅本次会话走 SCNet
```

| profile | 端点 | 鉴权 | 默认模型 | catalog |
| --- | --- | --- | --- | --- |
| `minimax` | `https://api.minimaxi.com/v1` | `MINIMAX_API_KEY` | `MiniMax-M3` | `minimax-catalog.json` |
| `nativex` | `https://ailink.nativex.com/v1` | `NATIVEX_API_KEY` | `gpt-5.6-luna` | `nativex-catalog.json` |
| `kimi` | `https://api.kimi.com/coding/v1` | `KIMI_API_KEY` | `kimi-for-coding` | `kimi-catalog.json` |
| `zhipu`（别名 `bigmodel`） | `https://open.bigmodel.cn/api/v1` | `ZHIPU_API_KEY` | `glm-5.3` | `zhipu-catalog.json` |
| `scnet` | `https://api.scnet.cn/api/llm/v1` | `SCNET_API_KEY` | `DeepSeek-V4-Flash-0731` | `scnet-catalog.json` |

全部 provider 均 `wire_api = "responses"`、`requires_openai_auth = false`。启动时跳过 ChatGPT 登录。

## MCP 说明

当前 Codex **无稳定 MCP 配置入口**。统一 `agents` sync 对 Codex MCP 记为 `skip`。

```shell
dotf codex -c
dotf agents -c
scripts/agents/sync.sh codex   # skills 同步；MCP skip
python3 scripts/agents/doctor.py
```

详见 `agents/env/README.md`。

## 为什么不需要登录

Codex 默认走 OpenAI 登录流程（ChatGPT / API Key）。本配置全部是**自定义 provider**，显式声明 `requires_openai_auth = false`。启动 `codex` 时会直接跳过 ChatGPT 登录选择器，改用对应 `*_API_KEY` 鉴权。

## 配置说明

- `config.toml` - Codex **基础**配置（base），安装时与选中的 `*.config.toml` overlay、以及 `config.local.toml` 合并生成 `~/.codex/config.toml`（真实文件，非软链）。**不含 `projects`**（信任列表已本地化，见下节）
  - 默认 `model_provider = "minimax"` / `model = "MiniMax-M3"`；`-f` 会覆盖这几项
  - `[model_providers.*]` 一次声明全部 provider，切换只改顶层 model / catalog
  - `approval_policy` / `sandbox_mode` - 审批与沙箱策略
- `minimax.config.toml` / `nativex.config.toml` / `kimi.config.toml` / `zhipu.config.toml` / `scnet.config.toml` - 各 provider 的 overlay（codex 0.134+ 独立文件，安装到 `~/.codex/<name>.config.toml`）
- `model-catalogs/*.json` - 各 provider 的模型能力目录，`/model` 切换器的数据来源

> **踩坑**：国内 MiniMax key 打到海外站 `api.minimax.io` 会 `401 invalid api key`（Codex 正常、Pi/SDK 挂时常是这个）。  
> 专题：`repos/codeup/agent-data/knowledge/snippets/minimax-cn-vs-intl.md`

## projects 本地化（信任列表不入库）

Codex 首次信任一个项目时，会自动把 `[projects."<path>"]` 追加进 `~/.codex/config.toml`。这类内容**机器特定且动态变化**，混进仓库会污染 git（跨机器还会串入他人的路径）。因此本仓库采用「base + local 合并」方案：

| 文件 | 是否入库 | 作用 |
| --- | --- | --- |
| `agents/vendors/codex/config.toml` | ✅ 入库 | 稳定共享配置（model/provider/policy/tui 等），**不含 projects** |
| `agents/vendors/codex/config.local.toml` | ❌ gitignore | 本机 projects 及任意本地覆盖 |
| `~/.codex/config.toml` | — | 安装时由 base + profile overlay + local **合并生成**（普通文件，非软链） |
| `~/.codex/.dotf-profile` | — | 上次 `dotf codex -f` 选中的默认 provider |

`dotf codex` 每次都用 `config.toml`（base）+ 当前 profile overlay + `config.local.toml`（local）**重新覆盖生成** `~/.codex/config.toml`。因此：

- 稳定配置始终以仓库 `config.toml` 为单一来源；
- projects 走 `config.local.toml`（gitignore，不污染仓库）；
- 默认 provider 记在本机 `~/.codex/.dotf-profile`，下次不带 `-f` 重装仍保持；
- codex 运行时新写入 `~/.codex/config.toml` 的信任**不会自动同步**进 local——需手动把 `[projects."<path>"]` 块加入 `config.local.toml` 后重跑（否则下次安装会被覆盖，需重新确认一次，成本很低）。

> 这是 codex 的已知设计缺陷（[openai/codex#14601](https://github.com/openai/codex/issues/14601)、[#3120](https://github.com/openai/codex/issues/3120)），官方暂未支持 `projects` 独立文件，故由本仓库的安装脚本在外部解决。

### 新机初始化

```bash
cp agents/vendors/codex/config.local.toml.example agents/vendors/codex/config.local.toml
# 按需编辑其中的项目路径
dotf codex -c
```

### 新增 / 删除已信任的项目

直接编辑 `agents/vendors/codex/config.local.toml`，增删对应的 `[projects."<path>"]` 块，然后：

```bash
dotf codex -c
```

（`config.local.toml` 是 projects 的唯一来源，安装时会以其为准覆盖生成 `~/.codex/config.toml`。）

## 模型能力目录（model catalog）

通过 `model_catalog_json` 声明当前 provider 各模型的 reasoning level、system prompt、工具类型等。配置完成后，在 Codex CLI 中输入 `/model`，即可在列表中切换模型与 reasoning level。

`minimax-catalog.json`（及其他 `*-catalog.json`）常用字段：

| 字段 | 含义 |
| --- | --- |
| `slug` / `display_name` | 模型标识与展示名，需与 API 模型名一致 |
| `default_reasoning_level` | 默认 reasoning effort；非 `none` 值开启 Adaptive Thinking |
| `supported_reasoning_levels` | `/model` 中可切换的选项；`none`=关闭 thinking，`high`=Deep |
| `base_instructions` | 使用该模型时附加的基础 system prompt |
| `supports_reasoning_summaries` | 开启 Responses API reasoning 路径，`true` 才会发送 `reasoning.effort` |
| `input_modalities` | 支持的输入模态，`["text","image"]` 表示支持文本与图片 |
| `truncation_policy` | 上下文截断策略（按字节数限制） |

## 安装

1. 密钥存 senv `ai` 组（shell 经 `~/.config/zsh/modules/misc.zsh` 的 `eval $(senv env export)` 自动导出）：

   ```bash
   senv env set MINIMAX_API_KEY "<minimax key>" -g ai     # 默认 MiniMax
   senv env set NATIVEX_API_KEY "<公司网关 key>" -g ai   # NativeX
   senv env set KIMI_API_KEY "<kimi coding key>" -g ai    # Kimi For Coding
   senv env set ZHIPU_API_KEY "<智谱 coding plan key>" -g ai
   senv env set SCNET_API_KEY "<scnet key>" -g ai         # 官方名也可能是 SCNET_TOKEN_PLAN_API_KEY
   ```

2. 新开终端（或 `eval $(senv env export)`）后运行安装脚本：

   ```bash
   dotf codex -c
   # 或直接切 provider
   dotf codex -f kimi
   ```

   或者直接运行：
   ```bash
   bash scripts/config.sh codex
   ```

## 使用

```bash
codex                              # 交互式 TUI
codex exec "review this change"    # 单次执行
codex exec -m glm-5.3 "..."        # 指定模型（须属于当前 catalog）
```

在 TUI 中输入 `/model` 查看当前 catalog 的模型列表与 reasoning level。

> **验证网关模型的正确姿势**（2026-08-20 踩坑）：判断某模型能否给 codex 用，必须 `codex exec -m <model>` 真跑——裸 curl 发简单 Responses 请求**不会触发网关的 Responses→chat 协议转换**，会被上游直接拒绝（如 "you must provide a messages parameter"），据此判定"chat-only 不可用"是误判。catalog 只收录高频几个，其他模型可 `-m <slug>` 直用或自行加条目。

## 各 provider 备注

### MiniMax

国内站 `api.minimaxi.com`（不是海外站 `api.minimax.io`）。catalog 含 M3 / M2.7 / M2.5 等。

### NativeX

公司 newapi 网关。默认 `gpt-5.6-luna`；catalog 含 gpt-5.6-sol/terra/luna、deepseek-v4 两档（不含 gpt-5.3-codex）。

### Kimi For Coding

官方 Base URL 是 Chat Completions；现行 Codex 只发 `/v1/responses`。若直连失败，需要本地 Responses 网关（官方文档示例为 CC Switch）。catalog：`kimi-for-coding`、`kimi-for-coding-highspeed`、`k3-256k`、`k3`。

### 智谱 GLM Coding Plan（open.bigmodel.cn）

官方 Codex 端点已是 OpenAI Responses：`https://open.bigmodel.cn/api/v1`（不要用 Chat Completions 的 `/api/coding/paas/v4`）。默认 `glm-5.3`；`/model` 还可切 `glm-5.3-flash`（原生多模态、Coding Plan 额度约为 5.3 的 3 倍）/ `glm-5-turbo` / `glm-5.2` / `glm-5.1` / `glm-5`。`dotf codex -f bigmodel` 与 `-f zhipu` 相同。

### SCNet

OpenAI（含 Responses）：`https://api.scnet.cn/api/llm/v1`。Anthropic 端点 Codex 不用。默认 `DeepSeek-V4-Flash-0731`（平台标了 Responses）。catalog 收录平台列出的 Kimi / DeepSeek / 千问 / 智谱 / MiniMax；未标 Responses 的模型仍可在 `/model` 里看到，但 Codex 可能失败。SCNet 按市场价扣 Credits，选模时注意成本。

## 注意事项

- 认证使用 `env_key`，Codex 运行时从环境变量读密钥，配置文件本身不含敏感信息。
- `config.toml` 采用「base + profile overlay + local 合并生成」（非软链），以免 codex 自动写入的 projects 污染仓库；`model-catalogs`、`*.config.toml` 等只读资源仍以软链管理。
- 本配置**不需要** `codex login`，也不需要 `OPENAI_API_KEY`。
- 密钥存 senv `ai` 组；已开着的终端需重开或手动 `eval $(senv env export)` 才能拿到新加的 key。
- `~/.codex/` 下的其他状态文件（`auth.json`、`history.jsonl` 等）不纳入 dotfiles 管理。
