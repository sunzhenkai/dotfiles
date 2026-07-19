# Kitty 配置文档规格

本规格定义了 Kitty 配置选项中文文档的要求。

## ADDED Requirements

### Requirement: 文档结构

中文配置文档 SHALL 按功能分类组织，提高可读性和查找效率。

#### Scenario: 文档分类结构
- **WHEN** 用户查看 `config/terminals/kitty/configuration-zh.md`
- **THEN** 文档 SHALL 包含以下主要分类：
  1. 基础配置（启动、性能）
  2. 字体配置
  3. 颜色和主题
  4. 滚动缓冲区
  5. 鼠标设置
  6. 键盘快捷键
  7. 窗口和标签管理
  8. 布局系统
  9. 高级功能（Remote Control、Kittens 等）
- **THEN** 每个分类 SHALL 包含相关的配置选项和说明
- **THEN** 文档 SHALL 使用清晰的 Markdown 标题结构

#### Scenario: 配置选项描述
- **WHEN** 描述一个配置选项
- **THEN** 描述 SHALL 包含：选项名称、类型、默认值、功能说明
- **THEN** 对于枚举类型选项，SHALL 列出所有可用值
- **THEN** 对于复杂选项，SHALL 提供示例配置

### Requirement: 内容来源和准确性

中文文档 SHALL 基于 Kitty 官方文档（https://sw.kovidgoyal.net/kitty/conf/）翻译和总结。

#### Scenario: 从官方文档获取内容
- **WHEN** 编写中文文档
- **THEN** 内容 SHALL 从 Kitty 官方文档抓取
- **THEN** SHALL 优先翻译常用配置选项（80/20 法则）
- **THEN** 罕见配置选项 SHALL 提供官方文档链接作为参考

#### Scenario: 文档版本标注
- **WHEN** 文档开头或结尾
- **THEN** SHALL 明确标注文档基于的 Kitty 版本（如 v0.46）
- **THEN** SHALL 声明："完整配置选项请参考官方文档"
- **THEN** SHALL 提供官方文档的完整链接

#### Scenario: 翻译准确性
- **WHEN** 翻译配置选项说明
- **THEN** SHALL 保持技术术语的准确性（如 scrollback、pane、layout 等）
- **THEN** SHALL 使用简洁易懂的中文表述
- **THEN** 关键技术术语 SHALL 在括号中保留英文原文（首次出现时）

### Requirement: 常用配置选项

中文文档 SHALL 重点覆盖日常使用中常用的配置选项。

#### Scenario: 字体配置选项
- **WHEN** 描述字体相关配置
- **THEN** SHALL 包含：
  - `font_family`: 主字体配置
  - `font_size`: 字号大小
  - `bold_font`、`italic_font`、`bold_italic_font`: 字体变体
  - `symbol_map`: Nerd Font 图标映射
  - `adjust_line_height`: 行高调整
  - `adjust_column_width`: 列宽调整

#### Scenario: 颜色和主题选项
- **WHEN** 描述颜色相关配置
- **THEN** SHALL 包含：
  - `foreground`、`background`: 前景色和背景色
  - `color0` - `color15`: 16 色调板配置
  - `selection_foreground`、`selection_background`: 选择文本颜色
  - `cursor`、`cursor_text_color`: 光标颜色
  - `tab_bar_background`、`tab_bar_style`: 标签栏样式
  - `include`: 包含主题文件

#### Scenario: 滚动缓冲区选项
- **WHEN** 描述滚动相关配置
- **THEN** SHALL 包含：
  - `scrollback_lines`: 滚动缓冲区行数
  - `scrollback_pager`: 查看滚动缓冲区的 pager 命令
  - `scrollback_fill_enlarged_window`: 放大窗格时是否填充滚动内容
  - `wheel_scroll_multiplier`: 鼠标滚轮滚动倍数

#### Scenario: 窗口和布局选项
- **WHEN** 描述窗口管理相关配置
- **THEN** SHALL 包含：
  - `enabled_layouts`: 启用的布局列表
  - `window_border_width`: 窗口边框宽度
  - `window_margin_width`: 窗口边距宽度
  - `window_padding_width`: 窗口内边距宽度
  - `hide_window_decorations`: 隐藏窗口装饰
  - `remember_window_size`: 记住窗口大小

#### Scenario: 键盘快捷键选项
- **WHEN** 描述快捷键相关配置
- **THEN** SHALL 包含：
  - `map`: 基础快捷键映射语法
  - `kitty_mod`: 修改 **默认整组** `Ctrl+Shift+…` 绑定所用的修饰键（与本仓库 `Ctrl+a>…` Leader 风格**无关**）
  - `map_timeout`: 多键序列超时
  - `mouse_map`: 鼠标快捷键映射
  - `clear_all_shortcuts yes/no`: 清除所有默认快捷键

#### Scenario: 高级选项
- **WHEN** 描述高级功能配置
- **THEN** SHALL 包含：
  - `allow_remote_control`: 允许远程控制
  - `clipboard_control`: 剪贴板行为控制
  - `shell_integration`: Shell 集成配置
  - `startup_session`: 启动会话文件
  - `tab_bar_edge`: 标签栏位置

### Requirement: 示例和用例

中文文档 SHALL 为每个配置选项提供实际使用示例。

#### Scenario: 基础配置示例
- **WHEN** 提供字体配置示例
- **THEN** SHALL 展示完整的字体配置块：
  ```conf
  font_family      family="Maple Mono" wght=800
  bold_font        auto
  italic_font      auto
  bold_italic_font auto
  font_size 18.0
  ```
- **THEN** SHALL 说明各选项的作用

#### Scenario: 快捷键映射示例
- **WHEN** 提供快捷键配置示例
- **THEN** SHALL 展示常用的快捷键映射：
  ```conf
  map_timeout 2.0
  map ctrl+a>h neighboring_window left
  map ctrl+a>l neighboring_window right
  ```
- **THEN** SHALL 说明 **多键序列** `ctrl+a>…` 与 **`kitty_mod`**（默认快捷键前缀）之区别

#### Scenario: 布局配置示例
- **WHEN** 提供布局配置示例
- **THEN** SHALL 展示如何启用和配置布局：
  ```conf
  enabled_layouts splits
  # Splits 布局不需要额外选项
  ```
- **THEN** SHALL 列出其他可用的布局类型（Tall、Fat、Grid 等）

### Requirement: 故障排查

中文文档 SHALL 包含常见问题的排查指南。

#### Scenario: 字体显示问题
- **WHEN** 用户遇到字体不显示或显示异常
- **THEN** 文档 SHALL 提供检查步骤：
  1. 验证字体是否已安装
  2. 检查字体名称拼写
  3. 使用 `kitty +list-fonts` 查看可用字体
  4. 检查 `symbol_map` 配置
- **THEN** SHALL 提供解决方法

#### Scenario: 快捷键不工作
- **WHEN** 用户配置的快捷键不起作用
- **THEN** 文档 SHALL 提供排查步骤：
  1. 检查配置文件语法（使用 `kitty --debug-config`）
  2. 验证快捷键未被其他应用占用
  3. 检查 **`map_timeout`、多键序列** 或与 **`kitty_mod` 默认键** 的冲突
  4. 使用 `kitty +runpy 'from kitty.key_names import *; key_prog = KeyProg(); key_prog.write()'` 测试按键

#### Scenario: 配置不生效
- **WHEN** 用户修改配置后没有生效
- **THEN** 文档 SHALL 说明：
  - 配置修改需要重载（`Ctrl+Shift+F5` 或 `load_config_file`）
  - 配置文件位置必须正确（`~/.config/kitty/kitty.conf`）
  - 某些选项需要重启 Kitty 才能生效

### Requirement: 更新和维护

中文文档 SHALL 包含如何保持文档与 Kitty 版本同步的说明。

#### Scenario: Kitty 版本更新
- **WHEN** Kitty 官方发布新版本
- **THEN** 文档 SHALL 提醒用户检查新功能和配置选项
- **THEN** SHALL 提供查看变更日志的方法
- **THEN** SHALL 建议使用 `kitty +runpy 'from kitty.config import *; print(commented_out_default_config())'` 生成最新默认配置

#### Scenario: 配置验证
- **WHEN** 用户不确定配置是否正确
- **THEN** 文档 SHALL 介绍验证工具：
  - `kitty --debug-config`: 显示配置加载过程和错误
  - `kitty +runpy 'from kitty.config import *; load_config(); dump_config()'`: 输出有效配置
  - `Ctrl+Shift+F6` (debug_config): 在运行中查看有效配置
