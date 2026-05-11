## ADDED Requirements

### Requirement: Logseq 配置符号链接安装

系统 SHALL 支持通过 `make logseq` 或 `scripts/install-config.sh logseq` 将 dotfiles 仓库中的 `logseq/` 目录符号链接到 `~/.logseq`。

#### Scenario: 首次安装 Logseq 配置
- **WHEN** `~/.logseq` 不存在且运行 `make logseq`
- **THEN** 创建从 `~/.logseq` 指向 `<dotfiles>/logseq` 的符号链接，输出 "Installed: logseq"

#### Scenario: 已安装时跳过
- **WHEN** `~/.logseq` 是指向 `<dotfiles>/logseq` 的正确符号链接
- **THEN** 输出 "Already installed: logseq"，不执行任何操作

#### Scenario: 旧配置备份后安装
- **WHEN** `~/.logseq` 已存在且不是正确的符号链接
- **THEN** 将旧配置备份到 `~/.config/backups/logseq-<timestamp>`，然后创建新符号链接

### Requirement: Logseq 配置目录结构保持完整

安装后 `~/.logseq` SHALL 包含以下由 dotfiles 仓库管理的文件：
- `config/config.edn`：全局配置
- `config/plugins.edn`：插件列表声明
- `preferences.json`：偏好设置

#### Scenario: 验证安装后的文件结构
- **WHEN** Logseq 配置安装成功
- **THEN** `~/.logseq/config/config.edn`、`~/.logseq/config/plugins.edn`、`~/.logseq/preferences.json` SHALL 可读且内容与 dotfiles 仓库中一致
