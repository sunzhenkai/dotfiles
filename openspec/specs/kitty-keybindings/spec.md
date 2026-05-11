# Kitty 快捷键映射规格

本规格定义了 Kitty 快捷键系统的配置要求。

## ADDED Requirements

### Requirement: 前缀键模式（Leader 等价）

系统 SHALL 使用 **多键序列** `ctrl+a>…`（可选配合 `map_timeout`）模拟 WezTerm 的 Leader；**不**依赖将 `kitty_mod` 设为 `ctrl+a`（官方 `kitty_mod` 仅支持由修饰键组成的组合）。

#### Scenario: 多键序列配置
- **WHEN** 用户在 `kitty.conf` 中配置 `map ctrl+a>h neighboring_window left` 等序列键
- **THEN** 用户先按 `Ctrl+a`、再按 `h` SHALL 触发对应动作（与配置中 `ctrl+a>h` 一致）
- **WHEN** 使用 `map --new-mode` 定义子模式（如 `ctrl+a>r` 进入 resize）
- **THEN** 在模式内按键 SHALL 按 `--mode` 映射处理，直至 `pop_keyboard_mode`

#### Scenario: 前缀键冲突与超时
- **WHEN** `Ctrl+a` 与时间窗（`map_timeout`）内未完成序列
- **THEN** 序列 SHALL 超时取消（行为以 Kitty 实现为准）
- **THEN** 如遇与 shell/应用抢占 `Ctrl+a`，用户可调整首键、`map_timeout` 或使用 `--when-focus-on`（见官方 mapping 文档）

### Requirement: 窗格操作快捷键

系统 SHALL 提供完整的窗格操作快捷键映射。

#### Scenario: 窗格分割
- **WHEN** 用户按 `Ctrl+a` 后再按 `\`（`ctrl+a>backslash`）
- **THEN** Kitty SHALL 在当前窗格的右侧创建垂直分割（vsplit）
- **WHEN** 用户按 `Ctrl+a` 后再按 `-`（`ctrl+a>minus`）
- **THEN** Kitty SHALL 在当前窗格的下方创建水平分割（hsplit）
- **THEN** 新窗格 SHALL 使用与当前窗格相同的工作目录（若配置 `launch --cwd=current`）

#### Scenario: 窗格导航
- **WHEN** 用户使用 `ctrl+a>h` / `j` / `k` / `l`
- **THEN** Kitty SHALL 分别激活左 / 下 / 上 / 右相邻窗格
- **THEN** 导航 SHALL 在 tab 内的窗格间循环

#### Scenario: 窗格调整大小
- **WHEN** 用户经 `ctrl+a>r` 进入 resize 模式后按方向键或 `h`/`j`/`k`/`l`
- **THEN** Kitty SHALL 分别调用 `resize_window` 变窄/变宽/变高/变矮（与映射一致）
- **THEN** 退出 resize 模式 SHALL 使用 `pop_keyboard_mode`（本仓库映射为 `esc`）

#### Scenario: 交互式调整大小
- **WHEN** 用户按 `Ctrl+Shift+r` (start_resizing_window）
- **THEN** Kitty SHALL 进入调整大小模式
- **THEN** 屏幕 SHALL 显示调整大小的提示和快捷键
- **THEN** 用户可以用方向键调整窗格大小，按 `Esc` 退出

#### Scenario: 窗格关闭
- **WHEN** 用户按 `Ctrl+Shift+w`
- **THEN** Kitty SHALL 关闭当前窗格
- **WHEN** 这是 tab 中最后一个窗格
- **THEN** Kitty SHALL 询问是否关闭整个 tab

### Requirement: 滚动操作快捷键

系统 SHALL 提供滚动缓冲区的快捷键访问。

#### Scenario: 页面滚动
- **WHEN** 用户按 `Ctrl+Shift+PageUp`
- **THEN** Kitty SHALL 向上滚动一页
- **WHEN** 用户按 `Ctrl+Shift+PageDown`
- **THEN** Kitty SHALL 向下滚动一页
- **THEN** 每页 SHALL 对应屏幕内容

#### Scenario: 行滚动
- **WHEN** 用户按 `Ctrl+Shift+Up`
- **THEN** Kitty SHALL 向上滚动一行
- **WHEN** 用户按 `Ctrl+Shift+Down`
- **THEN** Kitty SHALL 向下滚动一行

#### Scenario: 滚动缓冲区查看
- **WHEN** 用户按 `Ctrl+Shift+h` (show_scrollback）
- **THEN** Kitty SHALL 在 less pager 中打开滚动缓冲区
- **THEN** 颜色和格式 SHALL 被保留
- **WHEN** 用户在 less 中输入 `/pattern`
- **THEN** less SHALL 搜索匹配的文本
- **WHEN** 用户按 `q`
- **THEN** less SHALL 关闭，返回终端

#### Scenario: 滚动到顶部/底部
- **WHEN** 用户按 `Ctrl+Shift+Home`
- **THEN** Kitty SHALL 滚动到缓冲区顶部
- **WHEN** 用户按 `Ctrl+Shift+End`
- **THEN** Kitty SHALL 滚动到缓冲区底部

### Requirement: 复制和粘贴快捷键

系统 SHALL 提供复制和粘贴文本的快捷键。

#### Scenario: 选择并复制文本
- **WHEN** 用户用鼠标选择文本（双击选择词，三击选择行）
- **THEN** Kitty SHALL 自动复制选择到系统剪贴板（如果配置了 `copy_on_select yes`）
- **WHEN** 用户按 `Ctrl+Shift+c`
- **THEN** Kitty SHALL 复制当前选择到剪贴板
- **WHEN** 没有选择时
- **THEN** Kitty SHALL 发送 SIGINT 信号（相当于 Ctrl+c）

#### Scenario: 粘贴文本
- **WHEN** 用户按 `Ctrl+Shift+v`
- **THEN** Kitty SHALL 从剪贴板粘贴文本
- **THEN** 文本 SHALL 被发送到当前窗格
- **THEN** ANSI 转义序列 SHALL 被正确处理

### Requirement: Tab 管理快捷键

系统 SHALL 提供创建和切换 tab 的快捷键。

#### Scenario: 创建新 tab
- **WHEN** 用户按 `Ctrl+Shift+t` (new_tab）
- **THEN** Kitty SHALL 创建新 tab
- **THEN** 新 tab SHALL 成为当前 tab
- **THEN** 新 tab SHALL 使用默认 shell

#### Scenario: 切换 tab
- **WHEN** 用户按 `Ctrl+Shift+]`
- **THEN** Kitty SHALL 切换到下一个 tab
- **WHEN** 用户按 `Ctrl+Shift+[`
- **THEN** Kitty SHALL 切换到上一个 tab
- **THEN** 切换 SHALL 在 tab 列表两端循环

#### Scenario: 关闭 tab
- **WHEN** 用户按 `Ctrl+Shift+q`
- **THEN** Kitty SHALL 关闭当前 tab
- **WHEN** 这是 OS 窗口中最后一个 tab
- **THEN** Kitty SHALL 关闭整个 OS 窗口

### Requirement: 窗口和布局快捷键

系统 SHALL 提供窗口管理和布局切换的快捷键。

#### Scenario: 创建新窗口
- **WHEN** 用户按 `Ctrl+Shift+Enter` (new_window）
- **THEN** Kitty SHALL 在当前 tab 中创建新窗格
- **THEN** 新窗格 SHALL 使用当前 tab 的布局规则放置

#### Scenario: 切换布局
- **WHEN** 用户按 `Ctrl+Shift+l` (next_layout）
- **THEN** Kitty SHALL 切换到下一个启用的布局
- **THEN** 布局 SHALL 在启用的布局列表中循环

#### Scenario: 全屏切换
- **WHEN** 用户按 `Ctrl+Shift+F11` (toggle_fullscreen）
- **THEN** Kitty SHALL 切换 OS 窗口的全屏状态
- **THEN** 全屏 SHALL 使用 native macOS 全屏模式（如果配置）

### Requirement: 其他实用快捷键

系统 SHALL 提供其他常用终端操作的快捷键。

#### Scenario: 清除终端
- **WHEN** 用户按 `Cmd+l`
- **THEN** Kitty SHALL 清除终端屏幕
- **THEN** 清除方式 SHALL 根据 `clear_terminal` 配置

#### Scenario: 打开配置文件
- **WHEN** 用户按 `Ctrl+Shift+F2` (edit_config_file）
- **THEN** Kitty SHALL 在默认编辑器中打开 `kitty.conf`
- **THEN** 如果文件被外部修改，Kitty SHALL 提示重载配置

#### Scenario: 命令面板
- **WHEN** 用户按 `Ctrl+Shift+F3` (command_palette）
- **THEN** Kitty SHALL 显示可搜索的命令面板
- **THEN** 用户 SHALL 可以搜索和执行任何映射的操作

### Requirement: 快捷键文档

系统 SHALL 提供完整的快捷键文档。

#### Scenario: 文档存在
- **WHEN** 用户查看 `kitty/keybindings.md`
- **THEN** 文档 SHALL 按功能分类（滚动、窗格、tab 等）
- **THEN** 每个快捷键 SHALL 显示：按键组合、功能描述
- **THEN** 文档 SHALL 使用 Markdown 格式，支持表格

#### Scenario: 文档与配置一致
- **WHEN** `kitty.conf` 中的快捷键被修改
- **THEN** `kitty/keybindings.md` SHALL 同步更新
- **THEN** 文档 SHALL 反映当前配置的所有快捷键
- **THEN** 过时或未使用的快捷键 SHALL 从文档中移除
