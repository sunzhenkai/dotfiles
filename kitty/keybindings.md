# Kitty 快捷键

> **说明（与 WezTerm 「Leader」的对应关系）**  
> Kitty 使用 **多键序列**：先按 `Ctrl+a`，再按第二个键，写作 `Ctrl+a` → `h`（配置中为 `ctrl+a>h`）。  
> 这与 WezTerm 的 Leader 行为一致；**不是**同时按住 `Ctrl+a` 与 `h`。

> **macOS**  
> 下文 `Ctrl` 指键盘上的 **Control（⌃）**；Kitty 自带部分 **`Cmd（⌘）** 快捷键，见「Kitty 默认补充」一节。  
> 终端内 **`Cmd+↑/↓`** 的滚动行为取决于系统/应用；若需可预测的行滚动，请用 Kitty 默认的 **`Ctrl+Shift+↑/↓`**。

## 滚动（自定义：`Ctrl+a` 前缀）

| 快捷键 | 功能 |
|--------|------|
| `Ctrl+a` → `[` | 向上滚动 **半页**（`remote_control scroll-window`） |
| `Ctrl+a` → `]` | 向下滚动 **半页** |
| `Ctrl+Shift+↑` | 向上滚动一行（Kitty 默认） |
| `Ctrl+Shift+↓` | 向下滚动一行（Kitty 默认） |
| `Ctrl+Shift+PageUp` | 向上滚动一页（Kitty 默认） |
| `Ctrl+Shift+PageDown` | 向下滚动一页（Kitty 默认） |

## 浏览滚动缓冲区（对应 WezTerm「复制模式」）

| 快捷键 | 功能 |
|--------|------|
| `Ctrl+a` → `v` | 在 pager（默认可为 less）中打开滚动缓冲区 **`show_scrollback`** |
| `Ctrl+Shift+h` | 同上（Kitty 默认，仍有效） |
| （pager 内）`q` | 退出 pager |

> **与 WezTerm 差异**：无内建 **vi 复制模式** 与 **矩形选区**；可在 pager 中搜索/复制，或配合鼠标与 `copy_on_select`。

## 窗格

| 快捷键 | 功能 |
|--------|------|
| `Ctrl+a` → `\` | 左右分栏（`launch --location=vsplit`） |
| `Ctrl+a` → `-` | 上下分栏（`launch --location=hsplit`） |
| `Ctrl+a` → `h` / `j` / `k` / `l` | 焦点移到左 / 下 / 上 / 右邻窗 |
| `⌘+↩`（macOS） | 切换全屏 **`toggle_fullscreen`**（本仓库覆盖 Kitty 默认的「新窗口」，在 `splits` 下后者会像分屏） |

## 调整窗格大小（对应 WezTerm `Leader+r` 子模式）

进入 **resize** 模式：先按 `Ctrl+a`，再按 `r`；随后在 **5 秒**内可多次按方向键或 **h/j/k/l**（与 `kitty.conf` 中 `--mode resize` 一致）。

| 快捷键（在 resize 模式下） | 功能 |
|------------------------------|------|
| `h` / `←` | 变窄 `resize_window narrower` |
| `l` / `→` | 变宽 `resize_window wider` |
| `k` / `↑` | 变高 `resize_window taller` |
| `j` / `↓` | 变矮 `resize_window shorter` |
| `Esc` | 退出 resize 模式 |

**其它方式**：`Ctrl+Shift+r`（部分平台为 **⌘+r**）进入 Kitty **交互式** 调整大小说明界面。

## 窗格导航子模式（对应 WezTerm `Leader+p`）

先按 `Ctrl+a`，再按 `p` 进入 **pane_nav** 模式，**1 秒**内可用 `h/j/k/l` 或方向键切换邻窗；`Esc` 退出。

## 其它

| 快捷键 | 功能 |
|--------|------|
| `Ctrl+a` → `c` | 命令面板 **`command_palette`** |
| `Ctrl+Shift+F3` | 打开命令面板（Kitty 默认，同上） |

## Kitty 默认补充（未清空默认快捷键）

以下为常用 **默认** 绑定（前缀一般为 `Ctrl+Shift+`，勿与上表混淆），完整列表见官方文档或命令面板。

| 快捷键 | 功能 |
|--------|------|
| `Ctrl+Shift+t` | 新标签页 |
| `Ctrl+Shift+q` | 关闭当前标签 |
| `Ctrl+Shift+]` / `[` | 下一标签 / 上一标签（部分键盘布局为 `Ctrl+Shift+right` / `left`） |
| `Ctrl+Shift+w` | 关闭当前窗格 |
| `Ctrl+Shift+c` / `Ctrl+Shift+v` | 复制 / 粘贴 |
| `Ctrl+Shift+f2` | 编辑配置文件 |
| `Ctrl+Shift+f5` | 重载配置 |
| `Ctrl+Shift+f6` | 查看当前生效配置 |
| `Ctrl+Shift+↩` | 新窗格（Kitty 默认 **`new_window`**；macOS 上原 `⌘+↩` 已改为上表全屏，新建窗格请用此键或 `Ctrl+a` → `\` / `-`） |
| `Ctrl+Shift+F11` / `⌃+⌘+f`（macOS） | 切换全屏（Kitty 默认，仍有效） |

## WezTerm → Kitty 能力对照（简要）

| WezTerm（原配置） | Kitty（本仓库） |
|-------------------|-----------------|
| 自定义 Lua 标签栏、箭头与右侧状态栏 | **未移植**；使用 Kitty 原生标签栏与主题 |
| `Leader+[` / `]` 半页滚动 | **支持**（`scroll-window` 小数页） |
| `Leader+v` 复制模式（vi / 矩形） | **部分**：`show_scrollback` + pager，无矩形选区 |
| `Leader+r` / `Leader+p` 子模式 | **支持**（`--new-mode resize` / `pane_nav`） |
