## Requirements

### Requirement: config.sh 不使用 Bash 4+ 特性

`config.sh` SHALL NOT 使用 `declare -A`（关联数组）或其他 Bash 4+ 特性。配置映射 SHALL 使用 case 语句函数实现，确保在 Bash 3.2（macOS 自带）下可正常运行。

#### Scenario: 用 /bin/bash (3.2) 直接运行 config.sh
- **WHEN** 执行 `/bin/bash scripts/lib/dispatch_config.sh --all`
- **THEN** 脚本正常运行，不报 `declare -A` 或语法错误

#### Scenario: 用 /bin/bash 列出配置
- **WHEN** 执行 `/bin/bash scripts/lib/dispatch_config.sh`（无参数）
- **THEN** 正确显示所有可用配置列表

#### Scenario: 用 /bin/bash 配置单个模块
- **WHEN** 执行 `/bin/bash scripts/lib/dispatch_config.sh nvim`
- **THEN** 正确执行 nvim 配置的 symlink 创建

### Requirement: 配置映射使用 case 函数对

配置映射 SHALL 通过两个函数实现：
- `get_config_def <name>`: 返回 `"source:target"` 字符串，未知名称返回非零退出码
- `get_all_config_names()`: 返回所有配置名（空格分隔，排序后）

两个函数中的配置项 SHALL 保持一致——每个出现在 `get_all_config_names()` 中的名称 SHALL 在 `get_config_def()` 中有对应 case 分支。

#### Scenario: get_config_def 已知配置
- **WHEN** 调用 `get_config_def "nvim"`
- **THEN** 返回 `"config/editors/nvim:~/.config/nvim"`，退出码为 0

#### Scenario: get_config_def 未知配置
- **WHEN** 调用 `get_config_def "nonexistent"`
- **THEN** 无输出，退出码为非零

#### Scenario: get_all_config_names 完整性
- **WHEN** 调用 `get_all_config_names()`
- **THEN** 返回所有已注册的配置名，包含 `iterm2`

### Requirement: iterm2 配置注册

`iterm2` SHALL 在配置映射中注册，映射关系为 `config/terminals/iterm2:~/.config/iterm2`。

#### Scenario: 配置 iterm2
- **WHEN** 执行 `scripts/lib/dispatch_config.sh iterm2`
- **THEN** 创建 `~/.config/iterm2` 到 dotfiles 的 `iterm2/` 的 symlink

#### Scenario: --list 包含 iterm2
- **WHEN** 执行 `scripts/lib/dispatch_config.sh --list`
- **THEN** 输出列表中包含 `iterm2`

### Requirement: config.sh 支持 --list-desc

`config.sh` SHALL 支持 `--list-desc` 选项，以 tab 分隔输出配置名和描述。

#### Scenario: 列出配置及描述
- **WHEN** 执行 `scripts/lib/dispatch_config.sh --list-desc`
- **THEN** 每行输出格式为 `<name>\t<description>`，与 install.sh 的 `--list-desc` 格式一致

### Requirement: homebrew.sh 自包含 OS 检测

`homebrew.sh` 的 `init_homebrew()` SHALL NOT 依赖外部设置的 `$ID` 变量。SHALL 在函数内部自行检测操作系统。

#### Scenario: 跳过 system 模块直接安装 homebrew
- **WHEN** 执行 `dotf homebrew -i`（不先运行 system 模块）
- **THEN** macOS 特有的包（pngpaste、ghostty）正确安装

### Requirement: 中英文输出统一

所有脚本中用户可见的 `echo` 输出 SHALL 使用简体中文。代码注释不做强制要求。

#### Scenario: 错误信息语言
- **WHEN** 模块脚本输出错误信息
- **THEN** 使用简体中文