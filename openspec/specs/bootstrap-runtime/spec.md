# bootstrap-runtime Specification

## Purpose
TBD - created by archiving change overhaul-dotfiles-lifecycle. Update Purpose after archive.
## Requirements
### Requirement: 最小 bootstrap 不依赖模块注册表
系统 SHALL 提供仅依赖系统 shell 与常见基础命令的 bootstrap 入口。该入口在 Python 与 PyYAML 可用前 SHALL NOT 读取 `modules.yaml`、调用模块查询 API 或复制完整模块安装逻辑。

#### Scenario: 新环境缺少 PyYAML
- **WHEN** 用户在已有 shell 但缺少 PyYAML 的环境运行 bootstrap
- **THEN** bootstrap SHALL 正常启动并识别缺失依赖
- **THEN** SHALL NOT 因加载模块注册表而提前失败

### Requirement: 基础运行时预检与引导
bootstrap SHALL 检测当前 OS、Python、PyYAML 及进入主流程所需的基础命令，并为缺失项输出可操作的安装引导。自动安装系统依赖前 SHALL 获得明确确认。

#### Scenario: 基础依赖完整
- **WHEN** bootstrap 检测到所有基础依赖可用
- **THEN** SHALL 委托进入 `dotf init` 主流程

#### Scenario: 基础依赖缺失
- **WHEN** bootstrap 检测到受支持平台缺少基础依赖
- **THEN** SHALL 输出缺失项和平台适用的修复方式
- **THEN** 未经确认 SHALL NOT 修改系统

#### Scenario: 不支持的平台
- **WHEN** bootstrap 无法识别或不支持当前平台
- **THEN** SHALL 以非零退出并输出人工安装前置条件

### Requirement: Bootstrap 不处理私密配置
bootstrap SHALL NOT 收集、打印、持久化或提交 API Key、凭据、内部地址及设备私密配置。

#### Scenario: 进入主初始化
- **WHEN** bootstrap 完成基础运行时准备
- **THEN** 凭据与本地覆盖 SHALL 继续由主流程或用户环境管理
- **THEN** bootstrap 日志 SHALL NOT 包含环境变量值
