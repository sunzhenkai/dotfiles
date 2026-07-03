# Codex Configuration

此配置用于 [OpenAI Codex](https://developers.openai.com/codex) CLI，默认通过 **MiniMax（MiniMax-M3）** 接入，同时保留 **智谱 AI（GLM Coding Plan）** 作为备选 provider。

## 配置说明

- `config.toml` - Codex 主配置文件，安装到 `~/.codex/config.toml`
  - `model_provider = "minimax"` - 默认使用自定义的 MiniMax provider
  - `model = "MiniMax-M3"` - 默认模型（1M 上下文窗口）
  - `model_context_window = 1000000` - MiniMax-M3 的上下文窗口大小
  - `base_url` - MiniMax API 端点（Responses API 协议）
  - `env_key = "MINIMAX_API_KEY"` - 从环境变量读取 API Key，无需硬编码
  - `wire_api = "responses"` - MiniMax 提供 Responses API 协议
  - `approval_policy` / `sandbox_mode` - 审批与沙箱策略

## Provider 对比

| Provider | 模型 | Base URL | 协议 | 环境变量 |
| --- | --- | --- | --- | --- |
| `minimax`（默认） | `MiniMax-M3` | `https://api.minimaxi.com/v1` | Responses API | `MINIMAX_API_KEY` |
| `zhipu`（备选） | `glm-4.7` / `glm-5.1` / `glm-5.2` 等 | `https://open.bigmodel.cn/api/coding/paas/v4` | OpenAI Chat Completion | `ZHIPU_API_KEY` |

## 安装

1. 在你的 shell 配置文件中设置 `MINIMAX_API_KEY` 环境变量：

   在 `~/.envrc` 中添加：
   ```bash
   export MINIMAX_API_KEY="your_actual_api_key_here"
   ```

   > MiniMax API Key 获取：[MiniMax 开放平台](https://platform.minimaxi.com/) > API Keys

   若需要使用智谱备选，可一并设置 `ZHIPU_API_KEY`：
   ```bash
   export ZHIPU_API_KEY="your_actual_api_key_here"
   ```
   > 个人版套餐：个人编程套餐 > 套餐概览，新建 API Key
   > 团队版套餐：团队编程套餐 > 我的套餐，获取 API Key（团队套餐 Key 与平台其他 API Key 不通用）

2. 重新加载 shell 配置：
   ```bash
   source ~/.envrc
   ```

3. 运行安装脚本：
   ```bash
   ./dotf codex
   ```

   或者直接运行：
   ```bash
   bash scripts/config.sh codex
   ```

## 使用

```bash
# 交互式 TUI（默认 MiniMax-M3）
codex

# 单次执行
codex exec "review this change"

# 临时切换模型
codex --model MiniMax-M3

# 临时切换回智谱备选 provider
codex --model-provider zhipu --model glm-5.2
```

## 注意事项

- 认证使用 `env_key`，Codex 运行时从 `MINIMAX_API_KEY`（默认）/ `ZHIPU_API_KEY`（备选）环境变量读取密钥，因此配置文件本身不含敏感信息，可直接以 symlink 方式管理。
- 若 `MINIMAX_API_KEY` 未设置，安装脚本会给出警告（但配置文件仍会安装）；运行 `codex` 时会因缺少密钥而报错。
- `~/.codex/` 下的其他状态文件（`auth.json`、`history.jsonl` 等）不纳入 dotfiles 管理。
