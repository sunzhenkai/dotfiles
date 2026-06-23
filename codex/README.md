# Codex Configuration

此配置用于 [OpenAI Codex](https://developers.openai.com/codex) CLI 通过智谱 AI（GLM Coding Plan）接入 GLM 模型。

## 配置说明

- `config.toml` - Codex 主配置文件，安装到 `~/.codex/config.toml`
  - `model_provider = "zhipu"` - 使用自定义的智谱 AI provider
  - `model = "glm-4.7"` - 默认模型（可按需改为 `glm-5.1` / `glm-5.2` 等）
  - `base_url` - 智谱 Coding Plan 编程端点（OpenAI Chat Completion 协议）
  - `env_key = "ZHIPU_API_KEY"` - 从环境变量读取 API Key，无需硬编码
  - `wire_api = "chat"` - 智谱当前提供 OpenAI Chat Completion 协议
  - `approval_policy` / `sandbox_mode` - 审批与沙箱策略

## 智谱编程端点

| 协议类型 | Base URL |
| --- | --- |
| OpenAI Chat Completion 协议 | `https://open.bigmodel.cn/api/coding/paas/v4` |
| Anthropic Message 协议 | `https://open.bigmodel.cn/api/anthropic` |

Codex 使用 OpenAI Chat Completion 协议，因此使用上表第一条 Base URL。

## 安装

1. 在你的 shell 配置文件中设置 `ZHIPU_API_KEY` 环境变量：

   在 `~/.envrc` 中添加：
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
# 交互式 TUI
codex

# 单次执行
codex exec "review this change"

# 临时切换模型
codex --model glm-5.1
```

## 注意事项

- 认证使用 `env_key`，Codex 运行时从 `ZHIPU_API_KEY` 环境变量读取密钥，因此配置文件本身不含敏感信息，可直接以 symlink 方式管理。
- 若 `ZHIPU_API_KEY` 未设置，安装脚本会给出警告，但配置文件仍会安装；运行 `codex` 时会因缺少密钥而报错。
- `~/.codex/` 下的其他状态文件（`auth.json`、`history.jsonl` 等）不纳入 dotfiles 管理。
