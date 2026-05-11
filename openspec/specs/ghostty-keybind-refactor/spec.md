## ADDED Requirements

### Requirement: Ghostty 快捷键无冲突
Ghostty 配置中所有 `keybind` 绑定 MUST NOT 存在同一条目被重复定义的情况。每个 `ctrl+a>key` 序列 SHALL 只绑定一个 action。

#### Scenario: 滚动键位可用
- **WHEN** 用户按下 `ctrl+a>[`
- **THEN** 终端执行 `scroll_page_up`（而非 `previous_tab`）

#### Scenario: 滚动键位可用（向下）
- **WHEN** 用户按下 `ctrl+a>]`
- **THEN** 终端执行 `scroll_page_down`（而非 `next_tab`）

#### Scenario: 垂直分割可用
- **WHEN** 用户按下 `ctrl+a>-`（minus）
- **THEN** 终端执行 `new_split:down`（而非 `decrease_font_size`）

#### Scenario: 字体缩小使用独立绑定
- **WHEN** 用户按下 `ctrl+a>ctrl+-`（ctrl+minus）
- **THEN** 终端执行 `decrease_font_size:1`

### Requirement: 主题配置单一来源
Ghostty 的主题 SHALL 仅在主配置文件 `ghostty/config` 中定义。`auto/` 目录下 MUST NOT 存在与主配置冲突的主题文件。

#### Scenario: 主配置主题生效
- **WHEN** Ghostty 启动
- **THEN** 使用 `config` 中 `theme = Ayu` 的定义

#### Scenario: auto 目录不覆盖主配置
- **WHEN** `ghostty/auto/` 目录存在自动生成的文件
- **THEN** 该文件不会覆盖主配置中的 `theme` 设置

### Requirement: 快捷键参考文档
`ghostty/keybindings.md` SHALL 存在，包含所有自定义快捷键的完整参考。文档格式 SHALL 与 `wezterm/keybindings.md` 风格一致（中文、Markdown 表格、分类清晰）。

#### Scenario: 文档覆盖所有自定义绑定
- **WHEN** 查看 `ghostty/keybindings.md`
- **THEN** 文档中列出的每个快捷键都与 `ghostty/config` 中的 `keybind` 行一一对应

#### Scenario: 文档标注 Leader 键
- **WHEN** 查看 `ghostty/keybindings.md`
- **THEN** 文档开头明确标注 Leader 序列为 `Ctrl+A`
