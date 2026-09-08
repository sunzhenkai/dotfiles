# dotf-tui-manager Specification

## Purpose
提供 `dotf tui` 作为模块、Skill、MCP 与状态漂移的**管理页面**：键盘直达、按键即时触发、不退出 TUI、状态就地刷新；批量操作走同一 plan / runner。
## Requirements
### Requirement: 顶层大类菜单

TUI 启动 SHALL 把五类（Modules、Skills、MCP、Status、Conflicts）显示为顶部 tab，并默认选中 Modules 的清单。用户 SHALL 通过 `Tab` / `Shift+Tab`（以及清单内的 `l` / `h`）在类间循环并立即切换内容，或按数字 `1`-`5` 直达对应类。`q` SHALL 退出 TUI。SHALL NOT 再单独占用一屏菜单、SHALL NOT 要求回车才进入该类。

#### Scenario: 启动显示顶部 tab
- **WHEN** 用户在 TTY 中运行 `dotf tui`
- **THEN** TUI SHALL 在顶部显示五类 tab（Modules / Skills / MCP / Status / Conflicts）
- **THEN** SHALL 默认展示 Modules 清单

#### Scenario: Tab 切类
- **WHEN** 用户按 `Tab`
- **THEN** TUI SHALL 切换到下一类并展示其清单
- **THEN** 按 `Shift+Tab` SHALL 切换到上一类

#### Scenario: 数字直跳
- **WHEN** 用户按 `1`-`5` 且焦点不在过滤输入框
- **THEN** TUI SHALL 直接切换到对应类的清单

### Requirement: 模块子菜单一行一项

Modules 子菜单 SHALL 为每个当前 OS 适用的模块渲染一行，包含：模块名、能力图标（`I` install / `C` config / `D` doctor / `U` uninstall / `X` deconfig）、状态字段、版本或路径（如有）。未声明的能力 SHALL 不渲染对应动作。底部状态栏 SHALL 始终列出移动快捷键（`j`/`k` 上下、`Ctrl-d`/`Ctrl-u` 半屏、`g g`/`G` 首末），并在光标落在一行时追加该行已声明动作的快捷键、动作名与简述。`j`/`k` 或方向键 SHALL 移动光标；`Ctrl-d` / `Ctrl-u` SHALL 下/上移动半屏；`g g` 跳第一行，`G` 跳最后一行。

#### Scenario: 一行一模块
- **WHEN** 进入 Modules 子菜单
- **THEN** 每个模块 SHALL 占一行
- **THEN** SHALL NOT 把 install / config / doctor / uninstall / deconfig 拆成多行

#### Scenario: vim 移动
- **WHEN** 焦点在 Modules 清单
- **THEN** 按 `j` SHALL 下移一行，按 `k` SHALL 上移一行

#### Scenario: 半屏移动
- **WHEN** 焦点在 Modules 清单且列表多于一屏
- **THEN** 按 `Ctrl-d` SHALL 下移约半个可见高度
- **THEN** 按 `Ctrl-u` SHALL 上移约半个可见高度

#### Scenario: 状态栏列出移动快捷键
- **WHEN** TUI 显示任意清单
- **THEN** 底部状态栏 SHALL 包含 `j/k` 上下、`C-d/C-u` 半屏、`gg/G` 首末

#### Scenario: 不展示未声明动作
- **WHEN** 模块未声明 `uninstall`
- **THEN** 该行 SHALL NOT 展示 uninstall 动作
- **THEN** SHALL NOT 提供对应快捷键
- **THEN** 状态栏 SHALL NOT 列出 uninstall

#### Scenario: 状态栏列出当前行动作
- **WHEN** 光标在已声明 uninstall 的模块行
- **THEN** 底部状态栏 SHALL 列出该行快捷键、动作名与简述（含 `u uninstall`）

### Requirement: 模块动作键即时触发

Modules 子菜单中光标所在行 SHALL 支持下列按键即时触发对应动作，**不退出 TUI**：按 `i` install、`c` config、`d` deconfig、`u` uninstall、`D` doctor、`r` retry。runner 完成后 TUI SHALL 就地刷新该行的状态字段，并把本会话的改动加入改动列表。

#### Scenario: 单键即时 install
- **WHEN** 光标在 `grepom` 行
- **THEN** 按 `i` SHALL 立即 spawn `dotf grepom --install`
- **THEN** TUI SHALL 留在 Modules 子菜单
- **THEN** 完成后该行状态 SHALL 刷新为 `installed`
- **THEN** 改动 SHALL 出现在本会话改动列表

#### Scenario: doctor 单键触发
- **WHEN** 光标在 `nvim` 行
- **THEN** 按 `D` SHALL 立即 spawn `dotf nvim --doctor`
- **THEN** TUI SHALL 弹出进度窗展示输出
- **THEN** 完成前 SHALL NOT 响应其它操作
- **THEN** 完成后按 Enter SHALL 关闭进度窗并就地刷新
- **THEN** TUI SHALL 不退出

### Requirement: 动作进度窗阻塞直到完成

TUI 发起的任何 spawn 动作（含单键即时动作与批量 Enter）SHALL 弹出进度窗，展示当前命令与输出。进度窗打开且动作未完成时 SHALL NOT 响应 tab 切换、退出、勾选或其它动作键；Enter / Esc / q SHALL NOT 关闭进度窗。完成后 SHALL 提示按 Enter 继续；用户确认后 SHALL 关闭进度窗并就地刷新受影响行。

#### Scenario: 完成前不能关掉进度窗
- **WHEN** 用户按 `i` 触发 install 且命令仍在运行
- **THEN** TUI SHALL 显示进度窗
- **THEN** 按 `q` / `Esc` / `Enter` / `Tab` SHALL NOT 关闭进度窗，也 SHALL NOT 切类或退出

#### Scenario: 完成后按 Enter 继续
- **WHEN** 进度窗中的动作已全部结束
- **THEN** 用户按 Enter SHALL 关闭进度窗
- **THEN** TUI SHALL 回到原清单并刷新状态

### Requirement: Skill 与 MCP 一行一项 + 动作键

Skills 子菜单 SHALL 一行一项，每项含 Skill id、来源（catalog / desired / available）、状态。MCP 子菜单 SHALL 一行一项，每项为 `(tool, server)`，含 enable / disable 状态。两个子菜单都 SHALL 支持 `a` apply、`x` remove 单键即时触发；状态变更后 SHALL 就地刷新。

#### Scenario: Skill apply 即时
- **WHEN** 光标在 Skill `foo` 行
- **THEN** 按 `a` SHALL 立即 spawn `dotf agents skill apply foo`
- **THEN** 完成后该行状态 SHALL 反映 overlay 已启用

#### Scenario: MCP remove 即时
- **WHEN** 光标在 MCP `(cursor, foo)` 行
- **THEN** 按 `x` SHALL 立即 spawn `dotf agents mcp remove foo --tool cursor`
- **THEN** 完成后该行状态 SHALL 反映 overlay 已停用

### Requirement: 模糊筛选与跳转

TUI SHALL 提供 `/` 触发 incremental filter，按当前子菜单的项目名 / id 模糊匹配；`Esc` 清除 filter；`g g` 跳第一行，`G` 跳最后一行；`Home` / `End` 跳当前视图首尾；`Ctrl-d` / `Ctrl-u` 下/上移动半屏。数字 `1`-`5` 保留给顶部 tab 直达，SHALL NOT 再用于行号跳转。

#### Scenario: 模糊过滤
- **WHEN** 用户在 Modules 子菜单按 `/` 输入 `grep`
- **THEN** TUI SHALL 只显示模块名 / id 匹配 `grep` 的行
- **THEN** 光标 SHALL 落在首个匹配行

#### Scenario: vim 跳转
- **WHEN** 用户按 `G`
- **THEN** 光标 SHALL 跳到当前过滤后列表的最后一行
- **WHEN** 用户按 `g g`
- **THEN** 光标 SHALL 跳到第一行

### Requirement: 状态只读回显

TUI SHALL 仅**读取**下列状态，不直接修改：模块 `XDG_STATE_HOME/dotf/modules-state.yaml`、managed manifest、`agents/env/overlay.{yaml,json}`、`journal`。状态未知 SHALL 显示 `unknown`（中性灰字），不允许伪装成 `installed` / `absent`。状态字段 SHALL 每 30 秒或动作完成后刷新一次。

#### Scenario: 未运行过 dotf 显示 unknown
- **WHEN** 模块从未在当前机器上被 `dotf` 处理过
- **THEN** TUI SHALL 显示状态 `unknown`
- **THEN** SHALL NOT 通过 `which bin` 或类似探针冒充成 installed / absent

#### Scenario: config 状态来自 manifest
- **WHEN** 模块的 managed manifest 不存在或全部 target drift
- **THEN** TUI SHALL 显示该模块 config 状态为 `drift` / `missing`
- **THEN** SHALL NOT 重新发明与 manifest 重复的事实记录

### Requirement: Status 与 Conflicts 页只读

Status 子菜单 SHALL 列出 `dotf status` 等价的模块状态汇总；Conflicts 子菜单 SHALL 列出 managed manifest 中 `changed` / `missing` / `conflict` / `permission` 的目标以及 journal 中 `status=failed` 的去重模块列表。两个页 SHALL 只读、不提供动作快捷键。

#### Scenario: Status 页只读
- **WHEN** 用户进入 Status 子菜单
- **THEN** SHALL 看到模块名 + 状态字段
- **THEN** 按 `i` / `c` 等动作键 SHALL NOT 触发任何动作

#### Scenario: Conflicts 列 journal 失败项
- **WHEN** journal 存在 `status=failed` 的记录
- **THEN** Conflicts 页 SHALL 列出对应模块名（去重）
- **THEN** SHALL NOT 触发自动 retry

### Requirement: 批量多选 + Enter 组装 plan

TUI SHALL 支持 `space` 在当前子菜单勾选 / 取消勾选多行。勾选行 SHALL 在清单中以 `[x]` 前缀与高亮样式区别于未勾选行（未勾选为 `[ ]`）。勾选后按 `Enter` SHALL 在 TUI 内组装 plan（包含所有勾选动作），委托现有 `planner.py` 与 `run_plan.sh` 执行（仍走 `/dev/tty` 确认），执行完后 SHALL 就地刷新所有受影响行的状态。`Ctrl-x` SHALL 在已有勾选时弹出 y/N 确认后清空当前子菜单的全部勾选；默认 SHALL 为 `N`。无勾选时 `Ctrl-x` SHALL NOT 弹出确认。

#### Scenario: 多选 install 一并跑
- **WHEN** 用户在 Modules 子菜单勾选 `nvim`、`kitty` 后按 `Enter`
- **THEN** TUI SHALL 生成对应 plan 并执行
- **THEN** 两行状态 SHALL 同时刷新

#### Scenario: 勾选行可见
- **WHEN** 用户在 Modules 子菜单对当前行按 `space`
- **THEN** 该行 SHALL 显示 `[x]` 前缀
- **THEN** 再按 `space` SHALL 恢复为 `[ ]`

#### Scenario: 清空勾选需确认
- **WHEN** 用户已勾选至少一行并按 `Ctrl-x`
- **THEN** TUI SHALL 弹出 y/N 提示
- **THEN** 默认 SHALL 为 N；用户未输入 y SHALL NOT 清空勾选
- **WHEN** 用户输入 y 确认
- **THEN** TUI SHALL 清空当前子菜单全部勾选
- **THEN** 各行 SHALL 恢复为 `[ ]`

#### Scenario: 批量确认仍走 /dev/tty
- **WHEN** 批量 plan 生成成功
- **THEN** 确认 SHALL 通过 `/dev/tty` 复用现有 y/N 流程
- **THEN** Textual SHALL NOT 在确认阶段额外弹交互

### Requirement: 危险动作的二次确认

`uninstall` / `deconfig` / `mcp remove` / `skill remove` SHALL 在按下对应快捷键后弹出 y/N 确认；默认 SHALL 为 `N`。`install` / `config` / `apply` SHALL 在 dotf 子命令自带 `--yes` 行为之外，TUI 自身不增加额外确认。

#### Scenario: uninstall 默认 N
- **WHEN** 光标在 `grepom` 行按 `u`
- **THEN** TUI SHALL 弹出 y/N 提示
- **THEN** 默认 SHALL 为 N；用户未输入 y SHALL NOT 触发 uninstall

#### Scenario: install 无额外确认
- **WHEN** 光标在模块行按 `i`
- **THEN** TUI SHALL NOT 弹 TUI 内部的 y/N
- **THEN** 确认由 dotf 子命令自身决定

### Requirement: 退出回显

TUI 退出（按 `q`）SHALL 在 stdout 打印一行 "本会话改动：" 后跟去重后的动作清单（如 `installed grepom`、`configured nvim`、`removed skill foo`）。无改动 SHALL 仅打印 "本会话无改动"。

#### Scenario: 退出有改动
- **WHEN** 用户本会话执行过 install / config / apply / remove
- **THEN** 退出前 stdout SHALL 出现 "本会话改动：..." 行
- **THEN** 每条改动 SHALL 对应一次成功结果（`changed`）

#### Scenario: 退出无改动
- **WHEN** 用户进入 TUI 后未触发任何动作
- **THEN** 退出前 stdout SHALL 仅打印 "本会话无改动"
