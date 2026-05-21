### Requirement: 模块执行耗时记录

`run_module()` SHALL 在每个模块执行前记录开始时间，执行后记录结束时间，并计算耗时。

#### Scenario: 记录成功模块的耗时
- **WHEN** `run_module("homebrew")` 被调用且模块执行成功（返回码 0）
- **THEN** 系统 SHALL 记录模块名 "homebrew"、耗时秒数、状态 "✓"
- **THEN** 输出 "✔ homebrew 完成 (Xm Ys)" 格式的耗时信息

#### Scenario: 记录失败模块的耗时
- **WHEN** `run_module("sdk")` 被调用且模块执行失败（返回码非 0）
- **THEN** 系统 SHALL 记录模块名 "sdk"、耗时秒数、状态 "✗"
- **THEN** 输出 "✗ sdk 失败 (Xm Ys)" 格式的耗时信息

#### Scenario: 模块耗时精度
- **WHEN** 模块执行耗时不足 1 秒
- **THEN** 耗时 SHALL 显示为 "0s"

#### Scenario: 模块耗时超过 1 分钟
- **WHEN** 模块执行耗时 125 秒
- **THEN** 耗时 SHALL 显示为 "2m 5s"

### Requirement: 全量安装耗时汇总表格

`--all` 模式下，所有模块执行完毕后 SHALL 输出汇总表格，包含每个已执行模块的名称、耗时和状态，以及总计耗时和成功数。

#### Scenario: 全量安装完成后的汇总
- **WHEN** `--all` 模式下所有模块执行完毕
- **THEN** SHALL 输出汇总表格，表头为 "安装耗时统计"
- **THEN** 表格中每一行包含：模块名（左对齐 14 字符）、耗时（右对齐）、状态（✓/✗）
- **THEN** 表格末尾 SHALL 包含总计行：总耗时和 "X/Y 成功" 格式的成功计数

#### Scenario: 交互模式不输出汇总表格
- **WHEN** 用户通过交互模式（逐个确认）执行模块
- **THEN** 每个模块完成后 SHALL 显示耗时信息
- **THEN** SHALL NOT 输出汇总表格

#### Scenario: 跳过的模块不在汇总中
- **WHEN** 用户在交互模式中跳过某个模块
- **THEN** 该模块 SHALL NOT 出现在耗时记录和汇总表格中

### Requirement: 计时工具函数

`common.sh` SHALL 提供以下计时工具函数，兼容 Bash 3.2+。

#### Scenario: timer_format 函数
- **WHEN** 调用 `timer_format 65`
- **THEN** SHALL 输出 "1m 5s"
- **WHEN** 调用 `timer_format 30`
- **THEN** SHALL 输出 "30s"
- **WHEN** 调用 `timer_format 0`
- **THEN** SHALL 输出 "0s"

#### Scenario: 兼容 Bash 3.2
- **WHEN** 在 macOS 系统自带的 Bash 3.2 环境中运行
- **THEN** 计时功能 SHALL 正常工作
- **THEN** SHALL NOT 使用关联数组（`declare -A`）
