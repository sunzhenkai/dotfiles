# config-layout Specification

## Purpose
规定仓库内应用配置、模块生命周期处理器与顶级元目录的存放位置，确保分类清晰、源路径与安装目标分离、约定式模块处理器目录不与应用配置重复。
## Requirements
### Requirement: 应用配置分类目录
应用配置实体 SHALL 位于 `config/<category>/<name>/`（或该目录下的约定文件），不得再以顶层 `<name>/` 作为配置源真相位置。分类至少包括：`shell`、`editors`、`terminals`、`multiplexers`、`desktop`、`tools`。

#### Scenario: 编辑器配置路径
- **WHEN** 检查 `nvim` 配置源
- **THEN** 其仓库路径 SHALL 为 `config/editors/nvim`（或其下约定入口）

#### Scenario: 终端配置路径
- **WHEN** 检查 `kitty` 配置源
- **THEN** 其仓库路径 SHALL 为 `config/terminals/kitty`

#### Scenario: 工具配置路径
- **WHEN** 检查 `logseq` 配置源
- **THEN** 其仓库路径 SHALL 为 `config/tools/logseq`

### Requirement: 元目录留在仓库根
下列目录 SHALL 保留在仓库根，不得迁入 `config/`：`agents/`、`bin/`、`scripts/`、`openspec/`、`assets/`。

#### Scenario: agents 域独立
- **WHEN** 检查仓库顶层
- **THEN** `agents/` 仍位于根目录
- **THEN** 顶层 SHALL NOT 再并列存放已迁入 `config/` 的 app 配置目录（如顶层 `nvim/`、`kitty/`）

### Requirement: 安装目标路径不变
分类迁移只改变仓库内源路径；安装目标（如 `~/.config/nvim`、`~/.logseq`）SHALL 保持既有约定，除非某模块单独变更需求另有规定。`~/.logseq` SHALL 为真实目录（按文件链接声明式配置），不得整目录软链进仓库。

#### Scenario: nvim 目标不变
- **WHEN** 执行 `nvim` 的配置安装
- **THEN** 目标仍为 `~/.config/nvim`，源为仓库内 `config/editors/nvim`

### Requirement: 模块处理器约定目录
模块生命周期处理器 SHALL 位于 `scripts/modules/<module>/`，动作文件名 SHALL 为 `install.sh`、`config.sh`、`doctor.sh`。应用配置实体 SHALL 继续位于 `config/<category>/<name>/`，处理器目录不得复制应用配置形成第二真相源。无工具特有逻辑的配置 SHALL 复用与注册表部署策略匹配的公共实现；整目录软链不得作为通用默认行为。

#### Scenario: Nvim 配置模块
- **WHEN** 检查 nvim 模块布局
- **THEN** nvim 声明式配置 SHALL 保持位于 `config/editors/nvim`
- **THEN** `~/.config/nvim` SHALL 为承载本机运行态的真实目录
- **THEN** nvim 专用生命周期逻辑如存在 SHALL 位于 `scripts/modules/nvim/`

#### Scenario: 无专用逻辑的软链模块
- **WHEN** 模块只需通用 copy、merge、render 或允许的只读 symlink 配置
- **THEN** SHALL 复用相应公共配置实现
- **THEN** SHALL NOT 复制一份同等逻辑到模块目录

#### Scenario: 仓库声明与运行态隔离
- **WHEN** 应用在其 HOME 配置根目录创建 cache、session、history、plugin、credential 或机器专属文件
- **THEN** 这些路径 SHALL 留在 HOME 真实目录
- **THEN** SHALL NOT 因配置部署而写入仓库源目录

### Requirement: 公共运行库与模块实现分离
可复用的 runner、planner、结果、路径与 symlink 安全逻辑 SHALL 位于明确的公共脚本库；模块目录 SHALL 只包含模块特有行为。模块处理器 SHALL NOT 反向维护模块清单或自行解析全部注册表。

#### Scenario: 特殊 merge 配置
- **WHEN** codex 等模块需要合并 base 与本地覆盖
- **THEN** merge 行为 SHALL 位于该模块处理器或稳定公共库
- **THEN** 顶层 config 调度 SHALL NOT 为模块名增加专用 case

### Requirement: 迁移后移除并行调度入口
所有模块迁入约定式布局后，旧 install/config 模块 case 与全量 source 列表 SHALL 被移除。迁移期兼容适配器 SHALL 标记为临时且不得成为新增模块入口。

#### Scenario: 新增模块
- **WHEN** 新增一个具备 install 或 config 能力的模块
- **THEN** SHALL 通过注册表声明和约定式处理器接入
- **THEN** SHALL NOT 修改顶层模块名 case

#### Scenario: 迁移完成
- **WHEN** 所有注册模块均通过约定式处理器或公共默认实现运行
- **THEN** 仓库 SHALL 不再保留旧模块调度 case 作为并行路径
