# Kitty 终端配置规格

本规格定义了 Kitty 终端的基础配置管理要求。

## ADDED Requirements

### Requirement: 配置文件组织

系统 SHALL 使用单一的 `kitty.conf` 文件来存储所有配置。

#### Scenario: 配置文件存在
- **WHEN** 用户在 `~/.config/kitty/` 目录下有 `kitty.conf` 文件
- **THEN** Kitty 启动时 SHALL 自动加载该配置文件
- **THEN** 配置文件 SHALL 支持 `#` 行注释
- **THEN** 配置文件 SHALL 使用 `key value` 格式，每行一个配置项

#### Scenario: 配置文件缺失
- **WHEN** 用户没有 `kitty.conf` 文件
- **THEN** Kitty SHALL 使用内置默认配置
- **THEN** 用户可以使用 `kitty +runpy 'from kitty.config import *; print(commented_out_default_config())'` 生成默认配置文件

### Requirement: 字体配置

系统 SHALL 支持 Maple Mono 系列字体作为主要字体，字号为 18pt。

#### Scenario: 字体配置正确
- **WHEN** 用户在 `kitty.conf` 中配置 `font_family "Maple Mono" wght=800`
- **WHEN** 字号设置为 `font_size 18.0`
- **THEN** Kitty SHALL 使用指定字体渲染文本
- **THEN** 字体 SHALL 应用粗体（wght=800）
- **THEN** Nerd Font 图标 SHALL 通过 `symbol_map` 正确显示

#### Scenario: 字体回退机制
- **WHEN** 主字体缺失某些 Unicode 字符
- **THEN** Kitty SHALL 自动回退到系统默认字体
- **THEN** 用户 SHALL 可以通过 `font_features` 选项配置 OpenType 特性

### Requirement: 主题配置

系统 SHALL 支持通过包含主题文件来应用 Gruvbox Light 配色方案。

#### Scenario: 主题文件包含
- **WHEN** 用户在 `kitty.conf` 中配置 `include themes/Gruvbox-Light.conf`
- **THEN** Kitty SHALL 加载主题文件中定义的所有颜色
- **THEN** 主题文件 SHALL 包含 16 种基本颜色（color0-15）和前景色、背景色
- **THEN** 配色方案 SHALL 立即应用到终端

#### Scenario: 主题文件缺失
- **WHEN** 指定的主题文件不存在
- **THEN** Kitty SHALL 启动失败并显示错误信息
- **THEN** 错误信息 SHALL 明确指出缺失的文件路径

### Requirement: 滚动缓冲区配置

系统 SHALL 配置滚动缓冲区容量为 100,000 行。

#### Scenario: 滚动缓冲区配置正确
- **WHEN** 用户在 `kitty.conf` 中配置 `scrollback_lines 100000`
- **THEN** Kitty SHALL 保留最多 100,000 行终端输出历史
- **THEN** 用户 SHALL 可以通过快捷键或鼠标滚动查看历史
- **THEN** 滚动缓冲区 SHALL 在终端关闭时被清除

#### Scenario: 滚动缓冲区过大
- **WHEN** 用户配置超过 1,000,000 行的滚动缓冲区
- **THEN** Kitty 可能会消耗大量内存
- **THEN** 建议使用 `scrollback_pager` 功能来查看历史，而非保存全部在内存中

### Requirement: 布局系统配置

系统 SHALL 配置 Splits 布局作为主要布局系统。

#### Scenario: Splits 布局启用
- **WHEN** 用户在 `kitty.conf` 中配置 `enabled_layouts splits`
- **THEN** Kitty SHALL 使用 Splits 布局作为默认布局
- **THEN** Splits 布局 SHALL 支持水平分割（vsplit）和垂直分割（hsplit）
- **THEN** Splits 布局 SHALL 支持旋转分割方向（`layout_action rotate`）

#### Scenario: 新窗格创建
- **WHEN** 用户触发 `launch --location=vsplit` 命令
- **THEN** Kitty SHALL 在当前窗格的右侧创建新窗格
- **WHEN** 用户触发 `launch --location=hsplit` 命令
- **THEN** Kitty SHALL 在当前窗格的下方创建新窗格
- **WHEN** 用户触发 `launch --location=split` 命令
- **THEN** Kitty SHALL 根据当前窗格的宽高比自动选择分割方向

### Requirement: 基础行为配置

系统 SHALL 配置适合 macOS 的基础终端行为。

#### Scenario: 剪贴板集成
- **WHEN** 用户配置 `copy_on_select yes`
- **THEN** 用户选择文本时 SHALL 自动复制到剪贴板
- **WHEN** 用户配置 `clipboard_control write-clipboard write-primary read-clipboard read-primary`
- **THEN** Kitty SHALL 支持读写系统剪贴板和主剪贴板（Linux）

#### Scenario: 远程控制
- **WHEN** 用户配置 `allow_remote_control yes`
- **THEN** Kitty SHALL 允许通过脚本或远程控制命令
- **THEN** 远程控制 SHALL 支持创建窗格、切换布局、更改颜色等操作

#### Scenario: 终端铃
- **WHEN** 用户配置 `audible_bell no`
- **THEN** 终端铃 SHALL 不发出声音
- **THEN** 可选地，用户可以配置 `visual_bell_duration` 来显示视觉提示
