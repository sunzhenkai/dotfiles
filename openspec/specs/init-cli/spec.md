## Requirements

### Requirement: 参数解析
脚本 SHALL 支持主体优先的调用模型：`dotf <module...> -i|-c|-ic`，以及无模块时的 `dotf -i|-c|-ic`（进入交互选择）。全量标志行为：
- `dotf -i -a` / `dotf --install --all`：仅安装全部（按当前 OS 适用性过滤）
- `dotf -c -a` / `dotf --config --all`：仅配置全部（按当前 OS 适用性过滤）
- `dotf -a` / `dotf --all`：安装全部 + 配置全部（按当前 OS 适用性过滤；不含专属 init 的系统包分发，除非 system 模块本身被包含）

`-ic` / `--install --config`（或等价组合）SHALL 对每个指定模块先执行 install 再执行 config；install 失败（非零退出）时 SHALL 终止该模块的 config 及后续模块。

动作优先旧语法（`dotf -i <module>`、`dotf -c <module>`、`dotf -i x -c y` 模式切换）SHALL NOT 再被接受。

`--all` 模式不得设置可跳过确认的全局绕过；每个模块仍需用户单独确认。所有确认提示 SHALL 默认 N（需显式输入 y/Y），用户不可通过直接回车跳过确认。

#### Scenario: 显示帮助
- **WHEN** 运行 `dotf`（无参数）或 `dotf -h`
- **THEN** 显示帮助信息，包含主体优先用法、选项、示例

#### Scenario: 安装指定模块
- **WHEN** 运行 `dotf sdk golang -i`
- **THEN** 依次对 sdk、golang 执行安装调度

#### Scenario: 配置指定模块
- **WHEN** 运行 `dotf nvim kitty -c`
- **THEN** 依次对 nvim、kitty 执行配置调度

#### Scenario: 安装并配置
- **WHEN** 运行 `dotf agents -ic`
- **THEN** 先安装 agents，成功后再配置 agents

#### Scenario: -ic 安装失败终止
- **WHEN** 运行 `dotf agents -ic` 且 agents 的 install 以非零退出
- **THEN** SHALL NOT 执行 agents 的 config
- **THEN** 进程以非零退出码结束

#### Scenario: 仅配置全部
- **WHEN** 运行 `dotf -c -a` 或 `dotf --config --all`
- **THEN** 仅配置全部适用模块，不执行安装全集

#### Scenario: 仅安装全部
- **WHEN** 运行 `dotf -i -a` 或 `dotf --install --all`
- **THEN** 仅安装全部适用模块，不执行配置全集

#### Scenario: 全部模式
- **WHEN** 运行 `dotf -a` 或 `dotf --all`
- **THEN** 先安装全部适用模块，再配置全部适用模块

#### Scenario: 旧语法拒绝
- **WHEN** 运行 `dotf -i sdk`
- **THEN** 以非零退出码失败并提示新用法（或等价的明确错误）

#### Scenario: 未知选项报错
- **WHEN** 运行 `dotf -x`
- **THEN** 显示错误信息和帮助，以非零退出码退出

#### Scenario: 未知模块名报错
- **WHEN** 运行 `dotf nonexistent -i`
- **THEN** 显示错误信息和可用模块列表，以非零退出码退出

### Requirement: 交互选择
当 `-i`、`-c` 或 `-ic` 未携带模块参数时，脚本 SHALL 显示对应能力下的模块编号列表，提示用户输入选择，支持数字序号、模块名称、`a`（全部）的混合输入。`-ic` 交互列表 SHALL 仅为同时具备 install 与 config 的模块，或对所选模块按能力分别执行并在缺失时按注册表规则报错（实施时取一致策略并在 help 说明；推荐列表展示所有模块，执行时按 `-ic` 规则校验）。

#### Scenario: 安装模式交互选择
- **WHEN** 运行 `dotf -i`（无模块参数）
- **THEN** 显示所有可安装模块的编号列表，提示用户输入选择

#### Scenario: 配置模式交互选择
- **WHEN** 运行 `dotf -c`（无模块参数）
- **THEN** 显示所有可配置模块的编号列表，提示用户输入选择

#### Scenario: 数字选择
- **WHEN** 用户输入 `1 3`
- **THEN** 选择第 1 和第 3 个模块执行

#### Scenario: 名称选择
- **WHEN** 用户输入 `sdk golang`
- **THEN** 选择 sdk 和 golang 模块执行

#### Scenario: 全部选择
- **WHEN** 用户输入 `a`
- **THEN** 选择当前模式列表中的所有模块执行

#### Scenario: 混合选择
- **WHEN** 用户输入 `1 sdk 3`
- **THEN** 解析为第 1 个模块、sdk、第 3 个模块，去重后执行

#### Scenario: 无效选择提示重新输入
- **WHEN** 用户输入无效内容（如 `xyz`）
- **THEN** 提示无效输入，重新显示列表

### Requirement: Bash 兼容性
脚本本身 SHALL 兼容 bash 3.2（macOS 系统自带版本），不使用关联数组等 bash 4+ 特性。模块映射可由注册表委托实现。

#### Scenario: 在 macOS 系统 bash 3.2 下运行
- **WHEN** 使用 `/bin/bash`（bash 3.2）执行 `bin/dotf -h`
- **THEN** 脚本正常运行，不报语法错误

### Requirement: Homebrew bash 自动检测
当调用 `scripts/config.sh` 时，脚本 SHALL 自动检测 `/opt/homebrew/bin/bash`，若存在则使用它执行；否则 fallback 到 `/bin/bash`。

#### Scenario: Homebrew bash 存在
- **WHEN** `/opt/homebrew/bin/bash` 存在且可执行
- **THEN** 使用 `/opt/homebrew/bin/bash` 执行 `config.sh`

#### Scenario: Homebrew bash 不存在
- **WHEN** `/opt/homebrew/bin/bash` 不存在
- **THEN** 使用 `/bin/bash` 执行 `config.sh`

### Requirement: 委托调用
脚本 SHALL 通过委托调用现有子脚本完成实际操作，不复制子脚本的逻辑。

#### Scenario: 安装委托
- **WHEN** 执行安装操作
- **THEN** 调用 `scripts/install.sh`，将模块名作为参数传入

#### Scenario: 配置委托
- **WHEN** 执行配置操作
- **THEN** 对每个选中的配置模块，分别调用 `scripts/config.sh <模块名>`

#### Scenario: 脚本路径解析
- **WHEN** 从任意目录执行 `bin/dotf`
- **THEN** 通过 `BASH_SOURCE[0]` 正确解析项目根目录，找到 `scripts/` 下的子脚本
