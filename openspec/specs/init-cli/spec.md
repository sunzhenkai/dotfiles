# init-cli Specification

## Purpose
提供主体优先的 `dotf` CLI：模块选择、install/config/doctor 动作组合、交互与全量模式，并委托现有子脚本执行。
## Requirements
### Requirement: 参数解析
脚本 SHALL 支持主体优先调用：`dotf <module...> -i|-c|-d|-ic|-id|-cd|-icd`（及长选项和分写等价组合），无模块动作进入交互选择。`-i -a`、`-c -a`、`-d -a` 分别表示全量安装、配置、诊断；单独 `-a` 表示全量安装和配置且不含 doctor。所有入口 SHALL 支持 `--dry-run`；会执行动作的入口 SHALL 支持显式 `--yes`。动作优先旧语法 SHALL NOT 被接受。

组合动作对每个模块 SHALL 按 install → config → doctor 执行；前序失败 SHALL 终止该模块后续动作及默认的后续模块。系统 SHALL 在确认前生成并展示或准备完整执行计划。默认确认 SHALL 为 N；`--yes` SHALL 作为唯一公开的全局自动确认方式，且不得绕过校验、备份或错误处理。

#### Scenario: 显示帮助
- **WHEN** 运行 `dotf`（无参数）或 `dotf -h`
- **THEN** 显示主体优先用法、动作组合、plan 控制选项和示例

#### Scenario: 安装指定模块
- **WHEN** 运行 `dotf sdk golang -i`
- **THEN** planner SHALL 生成包含 sdk、golang 及必要依赖的安装计划
- **THEN** 确认后 SHALL 按计划执行

#### Scenario: 配置指定模块
- **WHEN** 运行 `dotf nvim kitty -c`
- **THEN** planner SHALL 生成对应配置计划并在确认后执行

#### Scenario: 诊断指定模块
- **WHEN** 运行 `dotf nvim -d`
- **THEN** 对 nvim 执行 doctor 调度

#### Scenario: 安装配置诊断
- **WHEN** 运行 `dotf agents -icd`
- **THEN** SHALL 对 agents 按 install、config、doctor 顺序执行

#### Scenario: 安装并配置
- **WHEN** 运行 `dotf agents -ic`
- **THEN** 先安装 agents，成功后再配置 agents

#### Scenario: 配置并诊断
- **WHEN** 运行 `dotf agents -cd`
- **THEN** 先配置 agents，成功后再诊断 agents

#### Scenario: -ic 安装失败终止
- **WHEN** 运行 `dotf agents -ic` 且 agents 的 install 以非零退出
- **THEN** SHALL NOT 执行 agents 的 config
- **THEN** 进程以非零退出码结束

#### Scenario: 前序失败终止
- **WHEN** 组合动作中的 install 或 config 失败
- **THEN** 同一模块后续动作及默认的后续模块 SHALL NOT 执行
- **THEN** 进程 SHALL 以非零退出

#### Scenario: 仅配置全部
- **WHEN** 运行 `dotf -c -a`
- **THEN** 仅配置当前 OS 适用且具备 config 的全部计划模块

#### Scenario: 仅安装全部
- **WHEN** 运行 `dotf -i -a`
- **THEN** 仅安装当前 OS 适用且具备 install 的全部计划模块

#### Scenario: 仅诊断全部
- **WHEN** 运行 `dotf -d -a`
- **THEN** 仅诊断当前 OS 适用且具备 doctor 的全部计划模块

#### Scenario: 全部模式不含 doctor
- **WHEN** 运行 `dotf -a`
- **THEN** SHALL 先安装再配置全部适用计划模块
- **THEN** SHALL NOT 执行 doctor

#### Scenario: Dry-run
- **WHEN** 在有效动作请求后传入 `--dry-run`
- **THEN** SHALL 输出最终执行计划且不执行任何动作

#### Scenario: 自动确认
- **WHEN** 在有效动作请求后传入 `--yes`
- **THEN** SHALL 在计划校验成功后跳过交互确认执行

#### Scenario: 旧语法拒绝
- **WHEN** 运行 `dotf -i sdk`
- **THEN** SHALL 以非零退出并提示主体优先用法

#### Scenario: 未知选项报错
- **WHEN** 运行 `dotf -x`
- **THEN** 显示错误信息和帮助，以非零退出码退出

#### Scenario: 未知模块名报错
- **WHEN** 运行 `dotf nonexistent -i`
- **THEN** 显示错误信息和可用模块列表，以非零退出码退出

#### Scenario: --all 经计划确认而非逐模块确认
- **WHEN** 运行 `dotf -i -a` 且未传 `--yes`，用户通过计划确认
- **THEN** 系统 SHALL 按计划执行适用模块的 install
- **THEN** SHALL NOT 对每个模块再弹出「是否安装」类确认

### Requirement: 交互选择
当动作旗标（`-i`、`-c`、`-d` 或组合）未携带模块参数时，脚本 SHALL 显示对应能力下的模块编号列表，提示用户输入选择，支持数字序号、模块名称、`a`（全部）的混合输入。`-d` 交互列表 SHALL 为具备 doctor 能力的模块。含多动作的交互列表 SHALL 按能力展示可执行模块，或对所选模块按动作集合校验能力并在缺失时按注册表规则报错（实施时取一致策略并在 help 说明）。

#### Scenario: 安装模式交互选择
- **WHEN** 运行 `dotf -i`（无模块参数）
- **THEN** 显示所有可安装模块的编号列表，提示用户输入选择

#### Scenario: 配置模式交互选择
- **WHEN** 运行 `dotf -c`（无模块参数）
- **THEN** 显示所有可配置模块的编号列表，提示用户输入选择

#### Scenario: 诊断模式交互选择
- **WHEN** 运行 `dotf -d`（无模块参数）
- **THEN** 显示所有可诊断模块的编号列表，提示用户输入选择

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
CLI SHALL 将模块选择、依赖展开与动作排序委托给统一 planner，将动作执行委托给统一 runner；CLI SHALL NOT 复制处理器逻辑。runner SHALL 通过约定式模块目录或迁移期兼容适配器调用实现。

#### Scenario: 安装委托
- **WHEN** 执行安装计划
- **THEN** CLI SHALL 将计划交给 runner
- **THEN** runner SHALL 调用对应模块 install 处理器

#### Scenario: 配置委托
- **WHEN** 执行配置计划
- **THEN** runner SHALL 调用对应模块 config 处理器

#### Scenario: 诊断委托
- **WHEN** 执行诊断计划
- **THEN** runner SHALL 调用 L0 doctor 与适用的模块 L1 处理器

#### Scenario: 脚本路径解析
- **WHEN** 从任意目录执行 `bin/dotf`
- **THEN** SHALL 正确解析仓库根目录并找到 planner、runner 与模块目录

### Requirement: doctor 组合与 agents 诊断旗标
当动作集合包含 doctor 且模块为 `agents` 时，系统 SHALL 允许将 agents 诊断专用选项（如 `--json`、`--deep`、`--profile`）透传给 doctor 实现。这些选项 SHALL NOT 再作为 `config`/`sync` 的旁路挂载点。

#### Scenario: agents 诊断透传 deep
- **WHEN** 运行 `dotf agents -d --deep`
- **THEN** agents doctor SHALL 以 deep 模式运行

### Requirement: 状态与重试命令
CLI SHALL 提供 `dotf status` 与 `dotf retry` 独立命令，并支持适用的 `--profile`、`--json`、`--dry-run` 或 `--yes` 控制选项。两者 SHALL NOT 与模块动作旗标产生歧义。

#### Scenario: 查看状态
- **WHEN** 运行 `dotf status --profile remote`
- **THEN** SHALL 只读检查 remote profile 的期望环境

#### Scenario: 重试失败动作
- **WHEN** 运行 `dotf retry --yes`
- **THEN** SHALL 校验最近失败计划后非交互重试其中的 failed 动作

#### Scenario: 命令与动作混用
- **WHEN** 用户将 `status` 或 `retry` 与模块动作旗标以不兼容方式混用
- **THEN** CLI SHALL 在执行前以非零退出并显示正确用法
