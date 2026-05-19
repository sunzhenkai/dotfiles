## ADDED Requirements

### Requirement: clangd 公式名从 Homebrew 安装列表中移除

`init_homebrew()` SHALL NOT 尝试通过 `brew install clangd` 安装 clangd。clangd 的功能 SHALL 由同行中已有的 `llvm` 包提供。

#### Scenario: C/C++ 工具安装行不包含 clangd
- **WHEN** 执行 `init_homebrew()` 中的 C/C++ 工具安装
- **THEN** `brew install` 命令中 SHALL 包含 `pkg-config ninja bear ctags valgrind llvm make cmake gcc`，且 SHALL NOT 包含 `clangd`

#### Scenario: clangd 二进制仍然可用
- **WHEN** `llvm` 包安装完成
- **THEN** `clangd` 二进制 SHALL 可通过 `$(brew --prefix llvm)/bin/clangd` 访问

### Requirement: Homebrew 安装行的包名有效性

`init_homebrew()` 中的每一个 `brew install` 调用 SHALL 只包含有效的 Homebrew formula 或 cask 名称。任何无效名称 SHALL 在安装前被跳过并输出警告。

#### Scenario: 无效 formula 不阻塞安装
- **WHEN** `brew install` 命令中包含一个不存在的 formula 名称
- **THEN** 该名称 SHALL 被跳过，输出警告信息，其余包继续安装

### Requirement: mysql-connector-c 替换为 mysql-client

`init_homebrew()` 中的 `brew install ... mysql-connector-c` SHALL 替换为 `mysql-client`，因为 `mysql-connector-c` 已被 Homebrew 弃用。

#### Scenario: 使用 mysql-client 替代 mysql-connector-c
- **WHEN** 执行开发工具行的 `brew install`
- **THEN** 使用 `mysql-client` 而非 `mysql-connector-c`
