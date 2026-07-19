## Requirements

### Requirement: 应用配置分类目录
应用配置实体 SHALL 位于 `config/<category>/<name>/`（或该目录下的约定文件），不得再以顶层 `<name>/` 作为配置源真相位置。分类至少包括：`shell`、`editors`、`terminals`、`multiplexers`、`desktop`、`tools`。

#### Scenario: 编辑器配置路径
- **WHEN** 检查 `nvim` 配置源
- **THEN** 其仓库路径 SHALL 为 `config/editors/nvim`（或其下约定入口）

#### Scenario: 终端配置路径
- **WHEN** 检查 `kitty` 配置源
- **THEN** 其仓库路径 SHALL 为 `config/terminals/kitty`

#### Scenario: 工具配置路径
- **WHEN** 检查 `logseq` 配置源
- **THEN** 其仓库路径 SHALL 为 `config/tools/logseq`

### Requirement: 元目录留在仓库根
下列目录 SHALL 保留在仓库根，不得迁入 `config/`：`agents/`、`bin/`、`scripts/`、`openspec/`、`assets/`。

#### Scenario: agents 域独立
- **WHEN** 检查仓库顶层
- **THEN** `agents/` 仍位于根目录
- **THEN** 顶层 SHALL NOT 再并列存放已迁入 `config/` 的 app 配置目录（如顶层 `nvim/`、`kitty/`）

### Requirement: 安装目标路径不变
分类迁移只改变仓库内源路径；symlink 安装目标（如 `~/.config/nvim`、`~/.logseq`）SHALL 保持既有约定，除非某模块单独变更需求另有规定。

#### Scenario: nvim 目标不变
- **WHEN** 执行 `nvim` 的配置安装
- **THEN** 目标仍为 `~/.config/nvim`，源为仓库内 `config/editors/nvim`
