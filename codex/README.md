# Codex Configuration

此配置用于 [OpenAI Codex](https://developers.openai.com/codex) CLI，通过 **MiniMax（MiniMax-M3）** 接入。**无需 OpenAI 账号登录**，只需设置 `MINIMAX_API_KEY` 环境变量即可使用。

## MCP 说明

当前 Codex **无稳定 MCP 配置入口**。统一 `agents` sync 对 Codex MCP 记为 `skip`。

```shell
dotf -c codex
dotf -c agents
scripts/agents/sync.sh codex   # skills 同步；MCP skip
python3 scripts/agents/doctor.py
```

详见 `agent-env/README.md`。

## 为什么不需要登录

Codex 默认走 OpenAI 登录流程（ChatGPT / API Key）。但本配置使用的是**自定义 provider**（MiniMax），其在配置中显式声明 `requires_openai_auth = false`。因此启动 `codex` 时会**直接跳过 ChatGPT 登录选择器**，转而用 `MINIMAX_API_KEY` 向 MiniMax 端点鉴权。

## 配置说明

- `config.toml` - Codex **基础**配置（base），安装时与 `config.local.toml` 合并生成 `~/.codex/config.toml`（真实文件，非软链）。**不含 `projects`**（信任列表已本地化，见下节）
  - `model_provider = "minimax"` - 使用自定义的 MiniMax provider
  - `model = "MiniMax-M3"` - 默认模型（1M 上下文窗口）
  - `model_context_window = 1000000` - MiniMax-M3 的上下文窗口大小
  - `model_catalog_json` - 指向自定义模型能力目录（见下节）
  - `base_url` - MiniMax API 端点（`https://api.minimaxi.com/v1`）
  - `env_key = "MINIMAX_API_KEY"` - 从环境变量读取 API Key，无需硬编码
  - `wire_api = "responses"` - MiniMax 提供 Responses API 协议
  - `requires_openai_auth = false` - 显式声明不要求 OpenAI 登录
  - `approval_policy` / `sandbox_mode` - 审批与沙箱策略
- `model-catalogs/custom-catalog.json` - 自定义模型能力目录，安装到 `~/.codex/model-catalogs/custom-catalog.json`

## projects 本地化（信任列表不入库）

Codex 首次信任一个项目时，会自动把 `[projects."<path>"]` 追加进 `~/.codex/config.toml`。这类内容**机器特定且动态变化**，混进仓库会污染 git（跨机器还会串入他人的路径）。因此本仓库采用「base + local 合并」方案：

| 文件 | 是否入库 | 作用 |
| --- | --- | --- |
| `codex/config.toml` | ✅ 入库 | 稳定共享配置（model/provider/policy/tui 等），**不含 projects** |
| `codex/config.local.toml` | ❌ gitignore | 本机 projects 及任意本地覆盖 |
| `~/.codex/config.toml` | — | 安装时由上面两者**合并生成**（普通文件，非软链） |

`dotf codex` 每次都用 `config.toml`（base）+ `config.local.toml`（local）**重新覆盖生成** `~/.codex/config.toml`。因此：

- 稳定配置始终以仓库 `config.toml` 为单一来源；
- projects 走 `config.local.toml`（gitignore，不污染仓库）；
- codex 运行时新写入 `~/.codex/config.toml` 的信任**不会自动同步**进 local——需手动把 `[projects."<path>"]` 块加入 `config.local.toml` 后重跑（否则下次安装会被覆盖，需重新确认一次，成本很低）。

> 这是 codex 的已知设计缺陷（[openai/codex#14601](https://github.com/openai/codex/issues/14601)、[#3120](https://github.com/openai/codex/issues/3120)），官方暂未支持 `projects` 独立文件，故由本仓库的安装脚本在外部解决。

### 新机初始化

```bash
cp codex/config.local.toml.example codex/config.local.toml
# 按需编辑其中的项目路径
dotf codex
```

### 新增 / 删除已信任的项目

直接编辑 `codex/config.local.toml`，增删对应的 `[projects."<path>"]` 块，然后：

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

1. 在你的 shell 配置文件中设置 `MINIMAX_API_KEY` 环境变量：

   在 `~/.envrc` 中添加：
   ```bash
   export MINIMAX_API_KEY="your_actual_api_key_here"
   ```

   > MiniMax API Key 获取：[MiniMax 开放平台](https://platform.minimaxi.com/) > API Keys

2. 重新加载 shell 配置：
   ```bash
   source ~/.envrc
   ```

3. 运行安装脚本（会同时安装 `config.toml` 与模型目录）：
   ```bash
   dotf codex
   ```

   或者直接运行：
   ```bash
   bash scripts/config.sh codex
   ```

## 使用

```bash
# 交互式 TUI（无需登录，直接使用）
codex

# 单次执行
codex exec "review this change"

# 临时切换模型 / reasoning level
codex --model MiniMax-M3
# 在 TUI 中输入 /model 查看模型列表与 reasoning level
```

## 关于智谱 GLM（暂不兼容）

早期版本（codex < 0.130）通过 `wire_api = "chat"`（OpenAI Chat Completion 协议）接入智谱 GLM Coding Plan。但 **codex 0.130+ 已彻底移除 `wire_api = "chat"` 支持，仅支持 Responses API**。而智谱 GLM Coding Plan 目前仅提供 Chat / Anthropic 协议（[社区已提交 /responses 支持的需求](https://github.com/zai-org/GLM-5/issues/39)），因此**暂无法在新版 codex 中保留智谱备选**。待智谱支持 `/responses` 端点后，可按相同方式新增 `[model_providers.zhipu]` 恢复。

## 注意事项

- 认证使用 `env_key`，Codex 运行时从 `MINIMAX_API_KEY` 环境变量读取密钥，因此配置文件本身不含敏感信息。
- `config.toml` 采用「base + local 合并生成」（非软链），以免 codex 自动写入的 projects 污染仓库；`model-catalogs` 等只读资源仍以软链管理。详见上文「projects 本地化」一节。
- 本配置**不需要** `codex login`，也不需要 `OPENAI_API_KEY`。
- 若 `MINIMAX_API_KEY` 未设置，安装脚本会给出警告（但配置文件仍会安装）；运行 `codex` 时会因鉴权失败而报错。
- `~/.codex/` 下的其他状态文件（`auth.json`、`history.jsonl` 等）不纳入 dotfiles 管理。
