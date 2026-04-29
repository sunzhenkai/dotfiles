## ADDED Requirements

### Requirement: 目标路径状态检测

`install_config()` SHALL 在创建 symlink 前检测目标路径的完整状态，区分以下五种情况：不存在、正确 symlink、指向错误位置的 symlink、broken symlink、普通文件或目录。

#### Scenario: 目标不存在
- **WHEN** 目标路径不存在且不是 symlink
- **THEN** 直接创建 symlink，不执行备份

#### Scenario: 目标是正确的 symlink
- **WHEN** 目标是 symlink 且 `readlink -f` 解析结果与期望路径一致
- **THEN** 输出 "Already installed" 并跳过

#### Scenario: 目标是指向错误位置的 symlink
- **WHEN** 目标是 symlink 且 `readlink -f` 解析结果与期望路径不一致，且 symlink 目标存在
- **THEN** 将目标 mv 到 `~/.config/backups/<basename>-<timestamp>`，然后 `ln -sf` 创建新 symlink

#### Scenario: 目标是 broken symlink
- **WHEN** 目标是 symlink 但指向的路径不存在
- **THEN** 不执行备份，直接 `ln -sf` 覆盖

#### Scenario: 目标是普通文件或目录
- **WHEN** 目标路径存在且不是 symlink
- **THEN** 将目标 mv 到 `~/.config/backups/<basename>-<timestamp>`，然后 `ln -s` 创建新 symlink

### Requirement: 集中备份目录

所有备份 SHALL 统一存放在 `~/.config/backups/` 目录下，命名格式为 `<原文件名>-<timestamp>`。

#### Scenario: 首次备份创建目录
- **WHEN** `~/.config/backups/` 不存在
- **THEN** 自动创建该目录

#### Scenario: 备份不污染 dotfiles 仓库
- **WHEN** 执行备份操作
- **THEN** 备份文件 SHALL NOT 存放在 dotfiles 仓库目录内

### Requirement: 安装输出包含备份路径

当执行备份时，SHALL 在输出中显示备份的完整路径，便于用户知晓旧配置去向。

#### Scenario: 执行备份时的输出
- **WHEN** 旧配置被备份
- **THEN** 输出包含 "Backed up <name> to <backup_path>" 格式的信息

#### Scenario: Logseq 配置备份时的输出
- **WHEN** `~/.logseq` 已存在且需要备份
- **THEN** 输出包含 "Backed up logseq to ~/.config/backups/logseq-<timestamp>" 格式的信息

### Requirement: logseq 注册为可用配置项

`logseq` SHALL 在 CONFIGS 映射和 Makefile CONFIGS 列表中注册，映射关系为 `logseq:~/.logseq`。

#### Scenario: 通过 Makefile 安装
- **WHEN** 运行 `make logseq`
- **THEN** 调用 `scripts/install-config.sh logseq` 执行安装

#### Scenario: 列出可用配置
- **WHEN** 运行 `scripts/install-config.sh` 不带参数
- **THEN** 输出的可用配置列表中 SHALL 包含 `logseq`

#### Scenario: 全量安装包含 logseq
- **WHEN** 运行 `make all` 或 `scripts/install-config.sh --all`
- **THEN** logseq 配置 SHALL 被包含在安装流程中

### Requirement: install_claude.sh symlink 修复

`install_claude.sh` 中处理 `.claude.json` symlink 的逻辑 SHALL 同步应用相同的检测和备份策略。

#### Scenario: .claude.json 是 broken symlink
- **WHEN** `~/.claude.json` 是指向不存在路径的 symlink
- **THEN** 不执行备份，直接 `ln -sf` 创建新 symlink

### Requirement: 幂等执行

重复运行同一配置的安装命令 SHALL 不产生备份文件或报错。

#### Scenario: 连续两次安装同一配置
- **WHEN** 运行 `make nvim` 后立即再次运行 `make nvim`
- **THEN** 第二次输出 "Already installed"，不产生备份
