# Codex Configuration

此配置用于 [OpenAI Codex](https://developers.openai.com/codex) CLI，默认通过 **NativeX 公司 newapi 网关**（`ailink.nativex.com`，模型 `gpt-5.3-codex`）接入；**无需 OpenAI 账号登录**，密钥 `NATIVEX_API_KEY` 存 senv `ai` 组。备用 MiniMax 直连（`codex --profile minimax`，`MINIMAX_API_KEY` 同在 senv `ai` 组）。

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

Codex 默认走 OpenAI 登录流程（ChatGPT / API Key）。但本配置使用的均是**自定义 provider**（NativeX / MiniMax），显式声明 `requires_openai_auth = false`。因此启动 `codex` 时会**直接跳过 ChatGPT 登录选择器**，转而用 `NATIVEX_API_KEY`（默认）或 `MINIMAX_API_KEY`（备用 profile）向对应端点鉴权。

## 配置说明

- `config.toml` - Codex **基础**配置（base），安装时与 `config.local.toml` 合并生成 `~/.codex/config.toml`（真实文件，非软链）。**不含 `projects`**（信任列表已本地化，见下节）
  - `model_provider = "nativex"` - 默认使用公司 newapi 网关 provider
  - `model = "gpt-5.3-codex"` - 默认模型（保守 context 窗口 400k）
  - `model_context_window = 400000` - 网关不透出真实窗口，取保守值宁可提前压缩
  - `model_catalog_json` - 指向 `nativex-catalog.json`（gpt-5.3-codex 元数据）
  - `env_key = "NATIVEX_API_KEY"` - 从环境变量读取 API Key（senv `ai` 组），无需硬编码
  - `wire_api = "responses"` - 网关 `/v1/responses` 端点已验证可用
  - `requires_openai_auth = false` - 显式声明不要求 OpenAI 登录
  - `[model_providers.minimax]` - 备用 provider（MiniMax 国内站 `api.minimaxi.com`，**不是** `api.minimax.io`）
  - `approval_policy` / `sandbox_mode` - 审批与沙箱策略
- `minimax.config.toml` - MiniMax 备用 profile（codex 0.134+ 独立文件机制，`codex --profile minimax` 激活，覆盖 model/context/catalog 回 MiniMax-M3）
- `model-catalogs/nativex-catalog.json` / `model-catalogs/custom-catalog.json` - 两套模型能力目录，安装到 `~/.codex/model-catalogs/`；nativex 版收录 gpt-5.3-codex（默认）+ gpt-5.6-sol / terra / luna + deepseek-v4-flash-0731 / deepseek-v4-pro-0813，`/model` 切换器的数据来源

> **踩坑**：国内 key 打到海外站 `api.minimax.io` 会 `401 invalid api key`（Codex 正常、Pi/SDK 挂时常是这个）。  
> 专题：`repos/codeup/agent-data/knowledge/snippets/minimax-cn-vs-intl.md`

## projects 本地化（信任列表不入库）

Codex 首次信任一个项目时，会自动把 `[projects."<path>"]` 追加进 `~/.codex/config.toml`。这类内容**机器特定且动态变化**，混进仓库会污染 git（跨机器还会串入他人的路径）。因此本仓库采用「base + local 合并」方案：

| 文件 | 是否入库 | 作用 |
| --- | --- | --- |
| `agents/vendors/codex/config.toml` | ✅ 入库 | 稳定共享配置（model/provider/policy/tui 等），**不含 projects** |
| `agents/vendors/codex/config.local.toml` | ❌ gitignore | 本机 projects 及任意本地覆盖 |
| `~/.codex/config.toml` | — | 安装时由上面两者**合并生成**（普通文件，非软链） |

`dotf codex` 每次都用 `config.toml`（base）+ `config.local.toml`（local）**重新覆盖生成** `~/.codex/config.toml`。因此：

- 稳定配置始终以仓库 `config.toml` 为单一来源；
- projects 走 `config.local.toml`（gitignore，不污染仓库）；
- codex 运行时新写入 `~/.codex/config.toml` 的信任**不会自动同步**进 local——需手动把 `[projects."<path>"]` 块加入 `config.local.toml` 后重跑（否则下次安装会被覆盖，需重新确认一次，成本很低）。

> 这是 codex 的已知设计缺陷（[openai/codex#14601](https://github.com/openai/codex/issues/14601)、[#3120](https://github.com/openai/codex/issues/3120)），官方暂未支持 `projects` 独立文件，故由本仓库的安装脚本在外部解决。

### 新机初始化

```bash
cp agents/vendors/codex/config.local.toml.example agents/vendors/codex/config.local.toml
# 按需编辑其中的项目路径
dotf codex
```

### 新增 / 删除已信任的项目

直接编辑 `agents/vendors/codex/config.local.toml`，增删对应的 `[projects."<path>"]` 块，然后：

```bash
dotf codex
```

（`config.local.toml` 是 projects 的唯一来源，安装时会以其为准覆盖生成 `~/.codex/config.toml`。）

## 模型能力目录（model catalog）

通过 `model_catalog_json` 声明 MiniMax-M3 的多模态输入、reasoning level（thinking 开关）、system prompt、工具类型等详细参数。配置完成后，在 Codex CLI 中输入 `/model`，即可在模型列表中看到 MiniMax-M3 及其可选 reasoning level。

`custom-catalog.json` 常用字段：

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
   senv env set NATIVEX_API_KEY "<公司网关 key>" -g ai   # 默认 provider（ailink.nativex.com）
   senv env set MINIMAX_API_KEY "<minimax key>" -g ai     # 备用 profile 用
   ```

2. 新开终端（或 `eval $(senv env export)`）后运行安装脚本（安装 `config.toml`、profile 与模型目录）：

   ```bash
   dotf codex
   ```

   或者直接运行：
   ```bash
   bash scripts/config.sh codex
   ```

## 使用

```bash
# 交互式 TUI（无需登录，直接走公司网关 gpt-5.3-codex）
codex

# 单次执行
codex exec "review this change"

# 临时切换网关上的其他模型（见 /v1/models；claude / gemini / kimi 等同样可用，但需先加进 catalog 才出现在 /model）
codex -m gpt-5.6-sol
# 在 TUI 中输入 /model 查看模型列表与 reasoning level
```

> **验证网关模型的正确姿势**（2026-08-20 踩坑）：判断某模型能否给 codex 用，必须 `codex exec -m <model>` 真跑——裸 curl 发简单 Responses 请求**不会触发网关的 Responses→chat 协议转换**，会被上游直接拒绝（如 "you must provide a messages parameter"），据此判定"chat-only 不可用"是误判；claude-sonnet / kimi-k3 / gemini-3.5-flash / deepseek-v4 两档均经 codex 实测通过。catalog 只收录高频几个，其他模型可 `-m <slug>` 直用或自行加条目。

## 备用 profile - MiniMax（直连切换）

需要绕开公司网关、直连 MiniMax 时（codex 0.134+ 的 profile 是**独立文件** `~/.codex/<name>.config.toml`，顶层键，不再是主配置里的 `[profiles.<name>]` 表；本目录的 `minimax.config.toml` 会随安装软链过去）：

```bash
codex --profile minimax
```

## 关于智谱 GLM（暂不兼容）

早期版本（codex < 0.130）通过 `wire_api = "chat"`（OpenAI Chat Completion 协议）接入智谱 GLM Coding Plan。但 **codex 0.130+ 已彻底移除 `wire_api = "chat"` 支持，仅支持 Responses API**。而智谱 GLM Coding Plan 目前仅提供 Chat / Anthropic 协议（[社区已提交 /responses 支持的需求](https://github.com/zai-org/GLM-5/issues/39)），因此**暂无法在新版 codex 中保留智谱备选**。待智谱支持 `/responses` 端点后，可按相同方式新增 `[model_providers.zhipu]` 恢复。

## 注意事项

- 认证使用 `env_key`，Codex 运行时从 `NATIVEX_API_KEY`（默认）/ `MINIMAX_API_KEY`（备用 profile）环境变量读取密钥，因此配置文件本身不含敏感信息。
- `config.toml` 采用「base + local 合并生成」（非软链），以免 codex 自动写入的 projects 污染仓库；`model-catalogs`、`*.config.toml` 等只读资源仍以软链管理。详见上文「projects 本地化」一节。
- 本配置**不需要** `codex login`，也不需要 `OPENAI_API_KEY`。
- 两个密钥都存 senv `ai` 组（shell 经 `eval $(senv env export)` 自动导出）；已开着的终端需重开或手动 re-eval 才能拿到新加的 key。
- `~/.codex/` 下的其他状态文件（`auth.json`、`history.jsonl` 等）不纳入 dotfiles 管理。
