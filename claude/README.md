# Claude Desktop Configuration

此配置用于 Claude Desktop 连接到智谱AI API。

## 安装

1. 在你的 shell 配置文件中设置 `ZHIPU_API_KEY` 环境变量：

   在 `~/.envrc` 中添加：
   ```bash
   export ZHIPU_API_KEY="your_actual_api_key_here"
   ```

   或者在 `~/.zshrc` 中添加相同内容。

2. 重新加载 shell 配置：
   ```bash
   source ~/.envrc
   ```

3. 运行安装脚本：
   ```bash
   make claude
   ```

   或者直接运行：
   ```bash
   bash scripts/install-config.sh claude
   ```

## 配置文件

- `~/.claude/settings.json` - Claude Desktop 主配置文件
  - `ANTHROPIC_AUTH_TOKEN` - API 密钥（从 `ZHIPU_API_KEY` 环境变量读取）
  - `ANTHROPIC_BASE_URL` - API 基础 URL（智谱 AI）
  - `API_TIMEOUT_MS` - API 超时时间
  - `CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC` - 禁用非必要流量
  - `ANTHROPIC_DEFAULT_HAIKU_MODEL` - 默认 Haiku 模型（glm-5.1）
  - `ANTHROPIC_DEFAULT_SONNET_MODEL` - 默认 Sonnet 模型（glm-5.1）
  - `ANTHROPIC_DEFAULT_OPUS_MODEL` - 默认 Opus 模型（glm-5.1）

- `~/.claude.json` - Claude Desktop 应用配置
  - `hasCompletedOnboarding` - 跳过初始设置向导

## 注意事项

- 如果 `ZHIPU_API_KEY` 环境变量未设置，安装脚本会显示警告，但仍然会安装配置文件。你需要手动编辑 `~/.claude/settings.json` 中的 `ANTHROPIC_AUTH_TOKEN` 字段。
- 每次修改环境变量后，需要重新运行安装脚本来更新配置文件。
