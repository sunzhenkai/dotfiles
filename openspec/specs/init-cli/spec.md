## ADDED Requirements

### Requirement: 参数解析
脚本 SHALL 支持 `-i`/`--install`、`-c`/`--config`、`-a`/`--all`、`-h`/`--help` 四种选项。`-i` 和 `-c` 为模式切换开关，后续非 flag 参数 SHALL 归入当前模式的模块列表。

#### Scenario: 显示帮助
- **WHEN** 运行 `./init`（无参数）或 `./init -h`
- **THEN** 显示帮助信息，包含用法、选项、模块列表、示例

#### Scenario: 安装指定模块
- **WHEN** 运行 `./init -i sdk golang`
- **THEN** 调用 `scripts/init.sh sdk golang`

#### Scenario: 配置指定模块
- **WHEN** 运行 `./init -c nvim kitty`
- **THEN** 依次调用 `scripts/install-config.sh nvim` 和 `scripts/install-config.sh kitty`

#### Scenario: 混合模式
- **WHEN** 运行 `./init -i sdk -c nvim`
- **THEN** 先执行安装 sdk，再执行配置 nvim

#### Scenario: 全部模式
- **WHEN** 运行 `./init -a` 或 `./init --all`
- **THEN** 调用 `scripts/init.sh --all`，再调用 `scripts/install-config.sh --all`

#### Scenario: 未知选项报错
- **WHEN** 运行 `./init -x`
- **THEN** 显示错误信息和帮助，以非零退出码退出

#### Scenario: 未知模块名报错
- **WHEN** 运行 `./init -i nonexistent`
- **THEN** 显示错误信息和可用模块列表，以非零退出码退出

### Requirement: 交互选择
当 `-i` 或 `-c` 无后续模块参数时，脚本 SHALL 显示对应模块的编号列表，提示用户输入选择，支持数字序号、模块名称、`a`（全部）的混合输入。

#### Scenario: 安装模式交互选择
- **WHEN** 运行 `./init -i`（无后续模块）
- **THEN** 显示所有安装模块的编号列表，提示用户输入选择

#### Scenario: 配置模式交互选择
- **WHEN** 运行 `./init -c`（无后续模块）
- **THEN** 显示所有配置模块的编号列表，提示用户输入选择

#### Scenario: 数字选择
- **WHEN** 用户输入 `1 3`
- **THEN** 选择第 1 和第 3 个模块执行

#### Scenario: 名称选择
- **WHEN** 用户输入 `sdk golang`
- **THEN** 选择 sdk 和 golang 模块执行

#### Scenario: 全部选择
- **WHEN** 用户输入 `a`
- **THEN** 选择当前模式的所有模块执行

#### Scenario: 混合选择
- **WHEN** 用户输入 `1 sdk 3`
- **THEN** 解析为第 1 个模块、sdk、第 3 个模块，去重后执行

#### Scenario: 无效选择提示重新输入
- **WHEN** 用户输入无效内容（如 `xyz`）
- **THEN** 提示无效输入，重新显示列表

### Requirement: Bash 兼容性
脚本本身 SHALL 兼容 bash 3.2（macOS 系统自带版本），不使用关联数组等 bash 4+ 特性。模块映射 SHALL 使用 case 匹配。

#### Scenario: 在 macOS 系统 bash 3.2 下运行
- **WHEN** 使用 `/bin/bash`（bash 3.2）执行 `./init`
- **THEN** 脚本正常运行，不报语法错误

### Requirement: Homebrew bash 自动检测
当调用 `scripts/install-config.sh` 时，脚本 SHALL 自动检测 `/opt/homebrew/bin/bash`，若存在则使用它执行；否则 fallback 到 `/bin/bash`。

#### Scenario: Homebrew bash 存在
- **WHEN** `/opt/homebrew/bin/bash` 存在且可执行
- **THEN** 使用 `/opt/homebrew/bin/bash` 执行 `install-config.sh`

#### Scenario: Homebrew bash 不存在
- **WHEN** `/opt/homebrew/bin/bash` 不存在
- **THEN** 使用 `/bin/bash` 执行 `install-config.sh`，若因关联数组报错则错误信息可被用户看到

### Requirement: 委托调用
脚本 SHALL 通过委托调用现有子脚本完成实际操作，不复制子脚本的逻辑。

#### Scenario: 安装委托
- **WHEN** 执行安装操作
- **THEN** 调用 `scripts/init.sh`，将模块名作为参数传入

#### Scenario: 配置委托
- **WHEN** 执行配置操作
- **THEN** 对每个选中的配置模块，分别调用 `scripts/install-config.sh <模块名>`

#### Scenario: 脚本路径解析
- **WHEN** 从任意目录执行 `./init`
- **THEN** 通过 `BASH_SOURCE[0]` 正确解析项目根目录，找到 `scripts/` 下的子脚本
