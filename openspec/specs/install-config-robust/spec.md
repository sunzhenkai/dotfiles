# install-config-robust Specification

## Purpose
让配置模块安装过程在目标路径状态异常、备份、原子写入与结果验证等方面保持健壮、可重复且可审计。
## Requirements
### Requirement: 目标路径状态检测
配置安装 SHALL 在修改目标前检查注册表策略、目标类型、父级路径和符号链接状态。`copy`、`merge`、`render` 目标 SHALL 为 HOME 下的真实文件或目录，且写入路径不得经由符号链接逃逸目标根；`symlink` 仅适用于注册表明确允许的只读非敏感目标。

#### Scenario: copy 目标不存在
- **WHEN** `strategy: copy` 的目标不存在
- **THEN** 系统 SHALL 创建真实目标并原子写入源内容
- **THEN** SHALL NOT 创建软链

#### Scenario: 可写目标是历史整目录软链
- **WHEN** 可写模块目标是指向 dotfiles 仓库的整目录软链
- **THEN** 系统 SHALL 只移除软链本身并创建 HOME 真实目录
- **THEN** SHALL NOT 跟随软链删除或移动仓库内容

#### Scenario: 写入路径包含非预期软链
- **WHEN** copy、merge、render 或备份目标自身或父级路径包含未声明的软链
- **THEN** 操作 SHALL 在写入前失败
- **THEN** 错误 SHALL 指明路径边界问题且不泄露文件内容

#### Scenario: 允许的只读软链已正确安装
- **WHEN** `strategy: symlink` 的目标指向期望源且被注册表允许
- **THEN** 操作 SHALL 返回 unchanged
- **THEN** SHALL NOT 创建备份

### Requirement: 集中备份目录
所有配置备份 SHALL 存放在仓库外的统一备份根目录，并按唯一 run id 和目标相对路径隔离。备份 SHALL 使用 `lstat` 语义且不得跟随符号链接复制其目标；备份根目录权限 SHALL 不宽于 `0700`，敏感普通文件备份权限 SHALL 不宽于 `0600`。

#### Scenario: 首次备份创建目录
- **WHEN** 统一备份根目录不存在
- **THEN** 系统 SHALL 创建该目录并设置不宽于 `0700` 的权限

#### Scenario: 同名目标备份
- **WHEN** 同一次或并发执行备份来自不同目录的同名文件
- **THEN** 两份备份 SHALL 使用不同路径
- **THEN** 已有备份 SHALL NOT 被覆盖

#### Scenario: 备份目标是软链
- **WHEN** 需要保留的旧目标是软链
- **THEN** 系统 SHALL 记录或移动软链本身
- **THEN** SHALL NOT 将软链指向内容复制为普通文件备份

#### Scenario: 敏感备份保留
- **WHEN** 敏感配置产生备份
- **THEN** 系统 SHALL 应用已声明的短期保留或禁用备份策略
- **THEN** doctor SHALL 能报告过期敏感备份而不读取或打印其内容

### Requirement: 安装输出包含备份路径

当执行备份时，SHALL 在输出中显示备份的完整路径，便于用户知晓旧配置去向。

#### Scenario: 执行备份时的输出
- **WHEN** 旧配置被备份
- **THEN** 输出包含 "Backed up <name> to <backup_path>" 格式的信息

#### Scenario: Logseq 旧目标为非目录时备份
- **WHEN** `~/.logseq` 已存在且既不是目录也不是符号链接
- **THEN** 将旧目标备份到 `~/.config/backups/` 后再创建真实目录
- **WHEN** `~/.logseq` 是指向仓库的整目录符号链接
- **THEN** 只删除该符号链接（不跟随删除仓库），不把 graphs/plugins 备份进 git

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

### Requirement: Docker 安装验证适配 Docker Desktop

`init_docker()` 中的 Docker 验证步骤 SHALL 根据运行环境选择验证方式。在 macOS（Docker Desktop）上 SHALL 使用非 sudo 验证。

#### Scenario: macOS Docker Desktop 验证
- **WHEN** 平台为 darwin 且 Docker 已安装
- **THEN** 使用 `docker run --rm hello-world`（不带 sudo）进行验证
- **THEN** 验证成功时输出 "Docker installation verified successfully!"
- **THEN** 验证失败时输出 "⚠️ Docker verification failed." 并提示启动 Docker Desktop

#### Scenario: Linux Docker 验证
- **WHEN** 平台非 darwin 且 Docker 已安装
- **THEN** 使用 `sudo docker run --rm hello-world` 进行验证（保持现有行为）

#### Scenario: Docker 未运行时的错误提示
- **WHEN** Docker 已安装但 daemon 未运行
- **THEN** 输出 SHALL 提示用户启动 Docker（macOS: "open -a Docker"；Linux: "sudo systemctl start docker"）
- **THEN** 脚本继续执行（不退出）

### Requirement: 配置写入原子且可验证
`copy`、`merge`、`render` 操作 SHALL 在目标同文件系统完成 staging 和格式校验，再通过原子替换提交。内容未变化时 SHALL 返回 unchanged 且不得创建备份。

#### Scenario: 生成内容未变化
- **WHEN** staging 内容与当前目标字节等价
- **THEN** 操作 SHALL 返回 unchanged
- **THEN** SHALL NOT 替换目标或创建备份

#### Scenario: 格式校验失败
- **WHEN** JSON、YAML、TOML 或声明格式的 staging 内容无法解析
- **THEN** 操作 SHALL 失败且保留原目标
- **THEN** SHALL 清理临时文件
