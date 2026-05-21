## ADDED Requirements

### Requirement: Python 包安装使用 uv 优先策略

所有平台（darwin/debian/arch/fedora/rhel）的系统初始化中，`pip3 install mysqlclient` 调用 SHALL 改为优先使用 `uv pip install --system mysqlclient`。

#### Scenario: uv 可用时使用 uv
- **WHEN** `uv` 命令在 PATH 中可用
- **THEN** 使用 `uv pip install --system mysqlclient` 安装
- **THEN** 命令 SHALL NOT 触发 PEP 668 错误

#### Scenario: uv 不可用时回退到 pip3
- **WHEN** `uv` 命令不在 PATH 中
- **THEN** 回退到 `pip3 install --break-system-packages mysqlclient`
- **THEN** 输出警告信息提示用户考虑安装 uv

#### Scenario: 安装失败时有清晰错误输出
- **WHEN** Python 包安装命令执行失败（非零退出码）
- **THEN** 输出包含 "⚠️ Failed to install mysqlclient" 的错误信息
- **THEN** 脚本继续执行后续步骤（不退出）

### Requirement: macOS 不使用 pip3 直接安装

`init_darwin()` SHALL NOT 直接调用 `pip3 install`，因为 macOS Homebrew Python 强制执行 PEP 668。

#### Scenario: macOS 使用 uv 安装 Python 包
- **WHEN** 在 darwin 平台执行系统初始化
- **THEN** Python 包安装 SHALL 使用 `uv pip install --system`
- **THEN** SHALL NOT 出现 `externally-managed-environment` 错误
