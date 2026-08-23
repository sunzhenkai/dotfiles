## Requirements

### Requirement: Logseq 配置按文件安装，禁止整目录软链
系统 SHALL 支持通过 `dotf logseq -c`（或等价配置调度）安装 Logseq 配置。`~/.logseq` SHALL 是真实目录，SHALL NOT 把整个目录符号链接到 dotfiles 仓库。仓库只管理声明式文件；`graphs/`、`plugins/`、`graphs.edn` 等运行时数据 SHALL 留在 `~/.logseq` 本机目录。

#### Scenario: 首次安装 Logseq 配置
- **WHEN** `~/.logseq` 不存在且运行 `dotf logseq -c`
- **THEN** 创建真实目录 `~/.logseq`，并将仓库中的 `config/config.edn`、`config/plugins.edn`、`preferences.json`、`settings/` 分别符号链接到该目录对应路径

#### Scenario: 拆除历史整目录软链
- **WHEN** `~/.logseq` 是指向 `<dotfiles>/config/tools/logseq` 的整目录符号链接且运行 `dotf logseq -c`
- **THEN** 删除该符号链接（不跟随删除仓库内容），创建真实目录，将仓库内已有的 `graphs/`、`plugins/`、`graphs.edn` 迁到 `~/.logseq`，再按文件链接声明式配置

#### Scenario: 已按文件安装时跳过
- **WHEN** `~/.logseq` 已是真实目录且声明式文件已正确链接
- **THEN** 输出已安装/跳过类提示，不执行破坏性操作

#### Scenario: 非软链的旧目标先备份
- **WHEN** `~/.logseq` 已存在且既不是目录也不是符号链接
- **THEN** 将旧目标备份到 `~/.config/backups/`，然后创建真实目录并链接配置文件

### Requirement: Logseq 配置目录结构保持完整
安装后 `~/.logseq` SHALL 包含以下由 dotfiles 仓库管理的文件（符号链接到仓库对应路径）：
- `config/config.edn`：全局配置
- `config/plugins.edn`：插件列表声明
- `preferences.json`：偏好设置
- `settings/`：插件设置（不得写入 API token）

#### Scenario: 验证安装后的文件结构
- **WHEN** Logseq 配置安装成功
- **THEN** `~/.logseq/config/config.edn`、`~/.logseq/config/plugins.edn`、`~/.logseq/preferences.json` SHALL 可读且内容与 dotfiles 仓库中 `config/tools/logseq/` 下对应文件一致
- **THEN** `~/.logseq` 本身 SHALL NOT 是指向仓库的符号链接
