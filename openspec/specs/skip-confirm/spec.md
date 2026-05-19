## Requirements

### Requirement: SKIP_CONFIRM 环境变量

`common.sh` 的 `confirm()` 函数 SHALL 检查 `SKIP_CONFIRM` 环境变量。当 `SKIP_CONFIRM=1` 时，`confirm()` SHALL 不弹出交互提示，直接返回成功（等同于用户确认）。

#### Scenario: SKIP_CONFIRM=1 时自动确认
- **WHEN** `SKIP_CONFIRM=1` 环境变量已设置，且代码调用 `confirm "是否安装?"`
- **THEN** 不弹出交互提示，函数返回 0（确认），输出提示信息（如 "自动确认: <prompt>"）

#### Scenario: SKIP_CONFIRM 未设置时正常交互
- **WHEN** `SKIP_CONFIRM` 环境变量未设置或值不为 `1`
- **THEN** `confirm()` 正常弹出交互提示，等待用户输入

#### Scenario: SKIP_CONFIRM=1 时拒绝默认值
- **WHEN** `SKIP_CONFIRM=1` 且 `confirm "是否安装?" "N"`（默认拒绝）
- **THEN** 仍然返回 0（确认），因为 `--all` 模式意味着用户已经选择了"全部执行"

### Requirement: --all 模式传递 SKIP_CONFIRM

`dotf` 和 `install.sh` 的 `--all` 模式 SHALL 设置 `SKIP_CONFIRM=1` 环境变量后调用子模块。

#### Scenario: dotf -a 无交互
- **WHEN** 执行 `dotf -a`
- **THEN** 所有 install 和 config 模块的 `confirm()` 调用自动确认，无交互提示

#### Scenario: dotf -i -a 无交互
- **WHEN** 执行 `dotf -i -a`
- **THEN** 所有 install 模块的 `confirm()` 调用自动确认

#### Scenario: dotf -c -a 无交互
- **WHEN** 执行 `dotf -c -a`
- **THEN** 所有 config 模块的 `confirm()` 调用自动确认

#### Scenario: 指定模块名时仍需确认
- **WHEN** 执行 `dotf -i sdk`（指定模块，非 --all）
- **THEN** `SKIP_CONFIRM` 未设置，模块内的 `confirm()` 正常弹出交互提示