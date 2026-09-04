# logseq-symlink-install Specification

## Purpose
让 Logseq 配置以文件级 symlink 方式安全安装，保证应用可写目录留在 HOME 真实目录、仓库不吞占运行态数据，且历史错误软链可被安全拆除。

## Requirements

### Requirement: Logseq 配置按文件安装，禁止整目录软链
系统 SHALL 支持通过 `dotf logseq -c` 安装 Logseq 声明式配置。`~/.logseq`、`~/.logseq/settings` 和其它应用可写目录 SHALL 是 HOME 下真实目录；仓库 SHALL 只管理明确列出的公共配置文件或字段，`graphs/`、`plugins/`、插件凭据和其它运行态 SHALL 留在本机目录。

#### Scenario: 首次安装 Logseq 配置
- **WHEN** `~/.logseq` 不存在且运行 `dotf logseq -c`
- **THEN** 系统 SHALL 创建真实目录及所需子目录
- **THEN** 声明式配置 SHALL 通过 copy 或 merge 安装，不得整目录链接 `settings/`

#### Scenario: 拆除历史整目录软链
- **WHEN** `~/.logseq` 是指向仓库的整目录软链
- **THEN** 系统 SHALL 只移除软链本身并创建 HOME 真实目录
- **THEN** SHALL NOT 跟随软链移动或删除仓库内容

#### Scenario: 拆除历史 settings 软链
- **WHEN** `~/.logseq/settings` 是指向仓库的软链
- **THEN** 系统 SHALL 只移除软链本身并创建真实目录
- **THEN** SHALL 将仓库声明的非敏感默认项安装到真实目录

#### Scenario: 插件设置包含私有字段
- **WHEN** 插件设置含 token、account、workspace、path 或其它本机私有字段
- **THEN** 同步 SHALL 保留 HOME 中已有值
- **THEN** SHALL NOT 将该值写回或复制到仓库

#### Scenario: 已按文件安装时跳过
- **WHEN** `~/.logseq` 已是真实目录且受管文件/字段与声明一致
- **THEN** 操作 SHALL 返回 unchanged
- **THEN** SHALL NOT 改动插件本机状态

#### Scenario: 非软链的旧目标先备份
- **WHEN** `~/.logseq` 已存在且既不是目录也不是符号链接
- **THEN** 系统 SHALL 先创建 no-follow 安全备份，再创建真实目录

#### Scenario: 重复安装
- **WHEN** 声明式配置与目标受管内容一致
- **THEN** 操作 SHALL 返回 unchanged
- **THEN** SHALL NOT 改动插件本机状态

### Requirement: Logseq 配置目录结构保持完整
安装后 `~/.logseq` SHALL 包含可读的 `config/config.edn`、`config/plugins.edn` 和 `preferences.json`，并包含真实的 `settings/` 目录。受管文件或字段 SHALL 与仓库声明一致，非受管插件字段 SHALL 保持本机值。

#### Scenario: 验证安装后的文件结构
- **WHEN** Logseq 配置安装成功
- **THEN** `~/.logseq` 与 `~/.logseq/settings` SHALL 均不是指向仓库的目录软链
- **THEN** 受管配置 SHALL 可读且通过格式校验
- **THEN** 插件凭据字段 SHALL NOT 出现在由本次安装产生的仓库变更中
