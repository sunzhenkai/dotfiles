# Ghostty 配置文档（中文）

> 完整的 Ghostty 终端模拟器配置参考文档，包含所有配置选项、快捷键说明、配置示例及与其他终端的对比。

---

## 目录

- [1. 配置概览](#1-配置概览)
- [2. 完整配置选项参考](#2-完整配置选项参考)
- [3. 快捷键配置](#3-快捷键配置)
- [4. 快捷键操作参考（按功能分类）](#4-快捷键操作参考按功能分类)
- [5. 我的配置说明](#5-我的配置说明)
- [6. 配置示例和模板](#6-配置示例和模板)
- [7. 与其他终端的对比](#7-与其他终端的对比)
- [8. 实用技巧和最佳实践](#8-实用技巧和最佳实践)

---

## 1. 配置概览

### 1.1 零配置哲学

Ghostty 设计为开箱即用，大多数用户无需任何配置即可使用。Ghostty 具有合理的默认值、内置默认字体（JetBrains Mono）、内置 Nerd Fonts 等。

如果您发现自己需要配置除主题之外的高度主观内容，并且认为这应该是默认值，请[发起讨论](https://github.com/ghostty-org/ghostty/discussions)。

### 1.2 文件位置

配置文件名为 `config.ghostty`（1.2.3 之前版本为 `config`），从以下位置按顺序加载：

**XDG 配置路径（所有平台）：**
- `$XDG_CONFIG_HOME/ghostty/config.ghostty`
- `$XDG_CONFIG_HOME/ghostty/config`
- 若未定义 `XDG_CONFIG_HOME`，默认为 `$HOME/.config`

**macOS 特定路径（仅 macOS）：**
- `$HOME/Library/Application Support/com.mitchellh.ghostty/config.ghostty`
- `$HOME/Library/Application Support/com.mitchellh.ghostty/config`

macOS 也支持 XDG 配置路径。若两个位置都存在，按上述顺序加载，后加载的文件中冲突值会覆盖先前的值。所有 macOS 特定文件都在所有 XDG 文件**之后**加载。

### 1.3 语法

Ghostty 使用简单直观的 `key = value` 语法：

```ini
# 语法是 "key = value"，等号周围的空格无关紧要
background = 282c34
foreground = ffffff

# 注释以 # 开头，仅在独立行有效
# 空行会被忽略

keybind = ctrl+z=close_surface
keybind = ctrl+d=new_split:right

# 空值将配置重置为默认值
font-family =
```

**语法要点：**
- 键名区分大小写，Ghostty 始终使用小写键
- 值可以加引号或不加引号：`font-family = "JetBrains Mono"` 等同于 `font-family = JetBrains Mono`
- 每个配置键也可作为 CLI 标志：`ghostty --background=282c34`

### 1.4 拆分为多个文件

使用 `config-file` 键拆分配置：

```ini
config-file = some/relative/sub/config
config-file = ?optional/config       # ? 前缀表示可选文件
config-file = /absolute/path/config
```

> **注意：** `config-file` 键在当前文件的**末尾**处理，因此其后的键不会覆盖加载文件中已设置的值。

### 1.5 重新加载配置

按 `cmd+shift+,`（macOS）或 `ctrl+shift+,`（Linux）重新加载配置。也可通过 `reload_config` 操作自定义快捷键。

> 部分配置无法在运行时重新加载，其他可能仅对新创建的终端生效。

### 1.6 离线参考文档

1. `$prefix/share/ghostty/docs` — HTML 和 Markdown 格式
2. `$prefix/share/man` — 手册页
3. CLI 命令：`ghostty +show-config --default --docs`
4. 源代码：[Config.zig](https://github.com/ghostty-org/ghostty/blob/main/src/config/Config.zig)
5. 查看其他用户的[配置示例](https://github.com/search?q=path%3Aghostty%2Fconfig&type=code)

---

## 2. 完整配置选项参考

### 2.1 字体配置

#### `font-family` / `font-family-bold` / `font-family-italic` / `font-family-bold-italic`

要使用的字体族。可重复指定以设置回退字体。

```ini
font-family = "JetBrains Mono"
font-family = "Noto Sans CJK SC"    # 中文回退字体
```

**要点：**
- 使用 `ghostty +list-fonts` 查看可用字体
- 可指定 `""`（空字符串）重置之前设置的值
- 特定样式（粗体等）不需要显式设置，会自动从常规字体查找
- macOS 默认使用 Apple Color Emoji，Linux 默认使用 Noto Emoji

#### `font-size`

字体大小（单位：磅）。默认值：`13`

```ini
font-size = 18
```

支持非整数，如 `13.5`（在 2x DPI 下对应 27px）。运行时更改仅影响未手动调整字体大小的终端。

#### `font-style` / `font-style-bold` / `font-style-italic` / `font-style-bold-italic`

字体的命名样式。设为 `false` 可禁用该样式。

```ini
font-style-bold = false    # 禁用粗体
```

#### `font-synthetic-style`

控制是否合成不存在的字体样式。默认值：`bold,italic,bold-italic`

```ini
font-synthetic-style = no-bold,no-italic    # 禁用粗体和斜体的合成
```

#### `font-feature`

应用字体特性（OpenType features）。

```ini
font-feature = -calt         # 禁用编程连字
font-feature = -calt,-liga,-dlig    # 禁用大多数连字
```

#### `font-variation` / `font-variation-bold` / `font-variation-italic` / `font-variation-bold-italic`

可变字体的轴值设置。

```ini
font-variation = wght=400    # 设置字重
```

常见轴：`wght`（字重）、`slnt`（倾斜）、`ital`（斜体）、`opsz`（光学尺寸）、`wdth`（宽度）

#### `font-codepoint-map`

强制将 Unicode 码点映射到特定字体。

```ini
font-codepoint-map = U+E000-U+E999=Nerd Font
```

#### `font-thicken`

加粗字体渲染（仅 macOS）。默认值：`false`

#### `font-thicken-strength`

加粗强度（0-255）。默认值：`255`

#### `font-shaping-break`

字体排印断点位置。默认值：`cursor`（在光标处断开，显示连字的单个字符）

可用选项：`cursor`

### 2.2 主题与配色

#### `theme`

使用的主题。可以是内置名称、自定义名称或绝对路径。

```ini
theme = Ayu
theme = light:Rose Pine Dawn,dark:Rose Pine    # 浅色/深色模式分别使用不同主题
```

- 使用 `ghostty +list-themes` 查看所有可用主题
- 自定义主题放在 `~/.config/ghostty/themes/` 目录下
- 主题文件本质上是 Ghostty 配置文件，可以设置任何安全选项

#### `background` / `foreground`

窗口的背景色和前景色。格式：`#RRGGBB`、`RRGGBB` 或 X11 颜色名。

```ini
background = #282c34
foreground = #ffffff
```

#### `background-image`

终端背景图片（PNG 或 JPEG）。仅支持文件路径。

#### `background-image-opacity`

背景图片不透明度（相对于 `background-opacity`）。默认值：`1`

#### `background-image-position`

背景图片位置。默认值：`center`

可选值：`top-left`、`top-center`、`top-right`、`center-left`、`center`、`center-right`、`bottom-left`、`bottom-center`、`bottom-right`

#### `background-image-fit`

背景图片适配方式。默认值：`contain`

可选值：`contain`（保持比例完整显示）、`cover`（保持比例覆盖）、`stretch`（拉伸填充）、`none`（不缩放）

#### `background-image-repeat`

是否重复背景图片。默认值：`false`

#### `palette`

256 色调色板配置。

```ini
palette = 0=#1d1f21    # 黑色
palette = 1=#cc6666    # 红色
# ... 0-255
```

#### `palette-generate`

是否从基础 16 色自动生成扩展 256 色调色板。默认值：`false`

#### `palette-harmonious`

反转自动生成的调色板颜色顺序。默认值：`false`

#### `bold-color`

粗体文本的颜色。设为 `bright` 使用亮色变体，或指定具体颜色。

#### `faint-opacity`

暗淡文本的不透明度。默认值：`0.5`

#### `minimum-contrast`

前景色与背景色的最小对比度（1-21）。默认值：`1`

- `1.1`：避免不可见的文字
- `3` 或更高：避免难以阅读的文字

### 2.3 选择高亮

#### `selection-foreground` / `selection-background`

选中区域的前景色和背景色。支持特殊值 `cell-foreground` 和 `cell-background`。

#### `selection-clear-on-typing`

输入时是否清除选中。默认值：`true`

#### `selection-clear-on-copy`

复制后是否清除选中。默认值：`false`

#### `selection-word-chars`

双击选择时的单词边界字符。默认值：`` \t'"│`|:;,()[]{}<>$ ``

### 2.4 搜索高亮

#### `search-foreground` / `search-background`

搜索匹配项的颜色（非聚焦）。默认值：黑字金底

#### `search-selected-foreground` / `search-selected-background`

当前选中搜索匹配项的颜色。默认值：黑字桃色底

### 2.5 光标设置

#### `cursor-color`

光标颜色。支持 `cell-foreground` 和 `cell-background` 特殊值。

#### `cursor-opacity`

光标不透明度（0-1）。默认值：`1`

#### `cursor-style`

光标样式。默认值：`block`

可选值：`block`（块）、`bar`（竖线）、`underline`（下划线）、`block_hollow`（空心块）

#### `cursor-style-blink`

光标是否闪烁。默认值：未设置（遵循 DEC Mode 12）

可选值：（空）、`true`、`false`

#### `cursor-text`

光标下文字的颜色。

#### `cursor-click-to-move`

是否允许通过点击提示符文本移动光标。需要 Shell 集成。默认值：`true`

### 2.6 鼠标设置

#### `mouse-hide-while-typing`

输入时隐藏鼠标。默认值：`false`

#### `mouse-shift-capture`

Shift 键与鼠标点击的行为。默认值：`false`

可选值：`true`、`false`、`always`、`never`

#### `mouse-reporting`

是否允许终端程序报告鼠标事件。默认值：`true`

#### `mouse-scroll-multiplier`

鼠标滚轮滚动距离倍数。默认值：`precision:1,discrete:3`

```ini
mouse-scroll-multiplier = 5                    # 所有设备
mouse-scroll-multiplier = precision:0.5,discrete:3    # 分别设置
```

#### `mouse-shift-capture`

Shift + 鼠标点击的行为。默认值：`false`

### 2.7 滚动设置

#### `scrollback-limit`

回滚缓冲区大小（行数）。默认值：`10000000`（1000 万行）

```ini
scrollback-limit = 100000
```

> 回滚缓冲区完全存在于内存中，设置越大，潜在内存使用越高。缓冲区按需分配。

#### `scrollbar`

何时显示滚动条。默认值：`system`

可选值：`system`（遵循系统设置）、`never`（从不显示）

#### `scroll-to-bottom`

何时滚动到底部。默认值：`keystroke,no-output`

可选选项：`keystroke`（按键时）、`output`（有新输出时）

### 2.8 窗口外观

#### `background-opacity`

窗口背景不透明度（0-1）。默认值：`1`（完全不透明）

```ini
background-opacity = 0.9
```

> macOS 原生全屏模式下背景透明不生效。更改此设置需要完全重启 Ghostty。

#### `background-opacity-cells`

是否将背景透明度也应用于有显式背景色的单元格。默认值：`false`

#### `background-blur`

背景模糊效果。默认值：`false`

```ini
background-blur = 20                # 模糊强度
background-blur = macos-glass-regular   # macOS 原生玻璃效果
```

macOS 26.0+ 支持特殊值：`macos-glass-regular`、`macos-glass-clear`

#### `alpha-blending`

Alpha 混合使用的颜色空间。macOS 默认 `native`，其他平台默认 `linear-corrected`。

可选值：`native`、`linear`、`linear-corrected`

#### `unfocused-split-opacity`

未聚焦分割的不透明度。默认值：`0.7`

#### `unfocused-split-fill`

未聚焦分割的遮罩颜色。默认为背景色。

#### `split-divider-color`

分割分隔线的颜色。

#### `split-preserve-zoom`

何时保持分割的缩放状态。默认值：`no-navigation`

设置为 `navigation` 可在导航分割时保持缩放状态。

### 2.9 窗口设置

#### `fullscreen`

是否全屏启动。默认值：`false`

可选值：`false`、`true`（原生全屏）、`non-native`（非原生全屏，无动画）、`non-native-visible-menu`、`non-native-padded-notch`

```ini
fullscreen = true
```

> **注意：** 非原生全屏模式不支持标签页。

#### `maximize`

是否最大化启动。默认值：`false`

#### `title`

强制设置窗口标题（忽略程序设置）。

#### `window-padding-x` / `window-padding-y`

窗口内边距（磅）。默认值：`2`

```ini
window-padding-x = 10,20    # 左10，右20
window-padding-y = 10       # 上下均为10
```

#### `window-padding-balance`

自动平衡内边距。默认值：`false`

#### `window-padding-color`

内边距区域的颜色。默认值：`background`

可选值：`background`、`extend`（延伸最近单元格颜色）、`extend-always`

#### `window-decoration`

窗口装饰偏好。默认值：`auto`

可选值：`none`（无装饰）、`auto`（自动）、`client`（客户端装饰）、`server`（服务端装饰）

#### `window-theme`

窗口主题。默认值：`auto`

可选值：`auto`、`system`、`light`、`dark`、`ghostty`

#### `window-colorspace`

窗口颜色空间（仅 macOS）。默认值：`srgb`

可选值：`srgb`、`display-p3`

#### `window-height` / `window-width`

初始窗口大小（以终端网格单元格为单位）。

#### `window-position-x` / `window-position-y`

初始窗口位置（像素）。

#### `window-save-state`

是否保存窗口状态。默认值：`default`

可选值：`default`、`never`、`always`

#### `window-step-resize`

按单元格大小调整窗口（仅 macOS）。默认值：`false`

#### `window-new-tab-position`

新标签的位置。默认值：`current`

可选值：`current`（当前标签后）、`end`（末尾）

#### `window-show-tab-bar`

标签栏显示方式（仅 GTK）。默认值：`auto`

可选值：`always`、`auto`（多个标签时显示）、`never`

#### `window-title-font-family`

窗口和标签标题使用的字体。

#### `window-subtitle`

窗口副标题内容（仅 GTK）。默认值：`false`

可选值：`false`、`working-directory`

#### `window-titlebar-background` / `window-titlebar-foreground`

窗口标题栏的颜色（仅 GTK，需 `window-theme = ghostty`）。

#### `window-vsync`

垂直同步（仅 macOS）。默认值：`true`

#### `window-inherit-working-directory`

新窗口是否继承上一个窗口的工作目录。默认值：`true`

#### `tab-inherit-working-directory`

新标签是否继承上一个标签的工作目录。默认值：`true`

#### `split-inherit-working-directory`

新分割是否继承上一个分割的工作目录。默认值：`true`

#### `window-inherit-font-size`

新窗口/标签是否继承字体大小。默认值：`true`

### 2.10 命令执行

#### `command`

运行的命令（通常是 Shell）。

```ini
command = /bin/zsh
command = direct:nvim foo    # 避免Shell展开
command = shell:nvim foo     # 强制使用Shell展开
```

#### `initial-command`

仅用于 Ghostty 启动时的第一个终端表面。CLI 的 `-e` 标志设置此项。

```ini
initial-command = fish
```

#### `wait-after-command`

命令退出后是否保持终端打开。默认值：`false`

#### `abnormal-command-exit-runtime`

异常退出判定阈值（毫秒）。默认值：`250`

#### `input`

启动时发送到命令的输入数据。

```ini
input = "Hello, world!"      # 直接发送文本
input = raw:\x15              # 发送控制字符
input = path:/path/to/file    # 发送文件内容
```

#### `env`

传递给终端命令的额外环境变量。

```ini
env = FOO=bar
env = BAR=baz
env = FOO=                   # 移除 FOO
```

### 2.11 滚动和链接

#### `scrollback-limit`

回滚缓冲区行数限制。默认值：`10000000`

#### `scrollbar`

滚动条显示方式。默认值：`system`

#### `link-url`

是否启用 URL 匹配。默认值：`true`

#### `link-previews`

链接预览显示。默认值：`true`

可选值：`true`、`false`、`osc8`（仅 OSC 8 链接）

### 2.12 剪贴板

#### `clipboard-read` / `clipboard-write`

程序读写剪贴板的权限（OSC 52）。

- `clipboard-read`：`ask`（默认）、`allow`、`deny`
- `clipboard-write`：`allow`（默认）、`ask`、`deny`

#### `clipboard-trim-trailing-spaces`

复制时是否修剪行尾空白。默认值：`true`

#### `clipboard-paste-protection`

粘贴安全检查（防止复制粘贴攻击）。默认值：`true`

#### `clipboard-paste-bracketed-safe`

括号粘贴是否被视为安全。默认值：`true`

#### `clipboard-codepoint-map`

复制时替换特定 Unicode 码点。

```ini
clipboard-codepoint-map = U+2500=U+002D    # 制表符横线 → 连字符
clipboard-codepoint-map = U+2502=U+007C    # 制表符竖线 → 管道符
```

#### `copy-on-select`

选中时自动复制。默认值：`true`

#### `right-click-action`

右键操作。默认值：`context-menu`

可选值：`context-menu`、`paste`、`copy`、`copy-or-paste`、`ignore`

### 2.13 终端类型

#### `term`

TERM 环境变量。默认值：`xterm-ghostty`

```ini
term = xterm-256color
```

#### `enquiry-response`

收到 ENQ（0x05）时的响应字符串。

### 2.14 Shell 集成

#### `shell-integration`

Shell 集成自动注入方式。默认值：`detect`

可选值：`none`、`detect`、`bash`、`elvish`、`fish`、`nushell`、`zsh`

**Shell 集成启用的功能：**
- 工作目录报告（新标签/分割继承目录）
- 提示符标记（`jump_to_prompt` 快捷键）
- 关闭终端时无需确认（如果在提示符处）
- 窗口大小调整时更好的提示符渲染

#### `shell-integration-features`

Shell 集成功能。默认值：`cursor,no-sudo,title,no-ssh-env,no-ssh-terminfo,path`

可用功能：
- `cursor` — 在提示符处将光标设为竖线
- `sudo` — 设置 sudo 包装器保留 terminfo
- `title` — 通过 Shell 集成设置窗口标题
- `ssh-env` — SSH 时自动转换 TERM 环境变量
- `ssh-terminfo` — SSH 时自动安装 Ghostty terminfo
- `path` — 将 Ghostty 二进制目录添加到 PATH

### 2.15 通知

#### `notify-on-command-finish`

命令完成通知。默认值：`never`

可选值：`never`、`unfocused`（仅未聚焦时）、`always`

#### `notify-on-command-finish-action`

通知方式。默认值：`bell,no-notify`

可选值：`bell`、`notify`

#### `notify-on-command-finish-after`

命令运行多久后发送通知。默认值：`5s`

### 2.16 标题报告

#### `title-report`

是否允许标题报告（CSI 21 t）。默认值：`false`

> **警告：** 这可能暴露敏感信息，甚至允许任意代码执行。

### 2.17 图像支持

#### `image-storage-limit`

图像数据存储限制（字节）。默认值：`320000000`（320MB）

### 2.18 调整度量值

所有 `adjust-*` 选项接受整数（像素）或百分比（如 `20%`），表示增量而非绝对值。

| 选项 | 描述 |
|------|------|
| `adjust-cell-width` | 单元格宽度调整 |
| `adjust-cell-height` | 单元格高度调整 |
| `adjust-font-baseline` | 文字基线位置调整 |
| `adjust-underline-position` | 下划线位置调整 |
| `adjust-underline-thickness` | 下划线粗细调整 |
| `adjust-strikethrough-position` | 删除线位置调整 |
| `adjust-strikethrough-thickness` | 删除线粗细调整 |
| `adjust-overline-position` | 上划线位置调整 |
| `adjust-overline-thickness` | 上划线粗细调整 |
| `adjust-cursor-thickness` | 光标粗细调整 |
| `adjust-cursor-height` | 光标高度调整 |
| `adjust-box-thickness` | 制表符粗细调整 |
| `adjust-icon-height` | Nerd Font 图标高度调整 |

#### `grapheme-width-method`

字形宽度计算方法。默认值：`unicode`

可选值：`legacy`（兼容旧程序）、`unicode`（Unicode 标准）

### 2.19 FreeType 设置（仅 Linux）

#### `freetype-load-flags`

FreeType 加载标志。默认值：`hinting,no-force-autohint,no-monochrome,autohint,light`

可用标志：`hinting`、`force-autohint`、`monochrome`、`autohint`、`light`

### 2.20 窗口管理

#### `confirm-close-surface`

关闭终端表面前是否确认。默认值：`true`

可选值：`true`、`false`、`always`

#### `quit-after-last-window-closed`

最后一个窗口关闭后是否退出。默认 macOS：`false`，Linux：`true`

#### `quit-after-last-window-closed-delay`

最后一个窗口关闭后延迟退出的时间（仅 Linux）。

#### `initial-window`

启动时是否创建初始窗口。默认值：`true`

#### `undo-timeout`

撤销操作的超时时间。默认值：`5s`（仅 macOS）

#### `focus-follows-mouse`

鼠标聚焦是否跟随。默认值：`false`

#### `resize-overlay`

调整大小时的覆盖层显示。默认值：`after-first`

可选值：`always`、`never`、`after-first`

#### `resize-overlay-position`

覆盖层位置。默认值：`center`

#### `resize-overlay-duration`

覆盖层显示时长。默认值：`750ms`

#### `click-repeat-interval`

重复点击间隔（毫秒）。默认值：`0`（系统默认）

#### `working-directory`

启动后的工作目录。默认值：`inherit`

可选值：绝对路径、`~/` 前缀路径、`home`、`inherit`

### 2.21 快速终端（Quick Terminal）

快速终端是一种从屏幕边缘滑入的下拉式终端（类似 Quake 风格）。

| 选项 | 描述 | 默认值 |
|------|------|--------|
| `quick-terminal-position` | 位置：`top`/`bottom`/`left`/`right`/`center` | `top` |
| `quick-terminal-screen` | 屏幕：`main`/`mouse`/`macos-menu-bar` | `main` |
| `quick-terminal-animation-duration` | 动画时长（秒） | `0.2` |
| `quick-terminal-autohide` | 失焦时自动隐藏 | macOS: `true`, Linux: `false` |
| `quick-terminal-space-behavior` | 切换 Space 行为：`move`/`remain` | `move` |
| `quick-terminal-keyboard-interactivity` | 键盘交互：`none`/`on-demand`/`exclusive` | `on-demand` |

### 2.22 Bell 设置

#### `bell-features`

Bell 功能。默认值：`no-system,no-audio,attention,title,no-border`

可用功能：`system`（系统通知）、`audio`（自定义声音）、`attention`（请求关注）、`title`（标题添加图标）、`border`（显示边框）

#### `bell-audio-path`

自定义 Bell 声音文件路径。

#### `bell-audio-volume`

Bell 音量（0.0-1.0）。默认值：`0.5`

### 2.23 自定义着色器

#### `custom-shader`

自定义 GLSL 着色器文件路径。兼容 Shadertoy 格式。

#### `custom-shader-animation`

着色器动画循环。默认值：`true`

可选值：`true`（聚焦时）、`false`（不动画）、`always`（始终动画）

### 2.24 键映射

#### `keybind`

快捷键绑定。详见[第 3 节](#3-快捷键配置)。

#### `key-remap`

修饰键重映射。

```ini
key-remap = ctrl=super          # Ctrl 键映射为 Super
key-remap = left_control=right_alt
```

### 2.25 macOS 专用设置

| 选项 | 描述 | 默认值 |
|------|------|--------|
| `macos-non-native-fullscreen` | 非原生全屏模式 | `false` |
| `macos-titlebar-style` | 标题栏样式：`native`/`transparent`/`tabs`/`hidden` | `transparent` |
| `macos-titlebar-proxy-icon` | 标题栏代理图标 | `visible` |
| `macos-window-buttons` | 窗口按钮（红绿灯） | `visible` |
| `macos-window-shadow` | 窗口阴影 | `true` |
| `macos-option-as-alt` | Option 键作为 Alt | 自动检测 |
| `macos-dock-drop-behavior` | Dock 拖放行为：`new-tab`/`new-window` | `new-tab` |
| `macos-hidden` | 隐藏 Dock 图标 | `never` |
| `macos-auto-secure-input` | 自动安全输入 | `true` |
| `macos-secure-input-indication` | 安全输入指示 | `true` |
| `macos-applescript` | AppleScript 支持 | `true` |
| `macos-icon` | 图标样式 | `official` |
| `macos-shortcuts` | Shortcuts 权限 | `ask` |
| `language` | GUI 语言（仅 GTK） | 系统默认 |

### 2.26 Linux/GTK 专用设置

| 选项 | 描述 | 默认值 |
|------|------|--------|
| `gtk-single-instance` | 单实例模式 | `detect` |
| `gtk-titlebar` | GTK 标题栏 | `true` |
| `gtk-tabs-location` | 标签栏位置：`top`/`bottom`/`hidden` | `top` |
| `gtk-titlebar-style` | 标题栏样式：`native`/`tabs` | `native` |
| `gtk-titlebar-hide-when-maximized` | 最大化时隐藏标题栏 | `false` |
| `gtk-toolbar-style` | 工具栏样式：`flat`/`raised`/`raised-border` | `raised` |
| `gtk-wide-tabs` | 宽标签 | `true` |
| `gtk-custom-css` | 自定义 CSS 文件 | — |
| `gtk-opengl-debug` | OpenGL 调试日志 | `false` |
| `gtk-quick-terminal-layer` | 快速终端层级 | `top` |
| `linux-cgroup` | cgroup 隔离 | `never` |
| `linux-cgroup-memory-limit` | 内存限制 | — |
| `linux-cgroup-processes-limit` | 进程数限制 | — |
| `linux-cgroup-hard-fail` | cgroup 失败是否阻止启动 | `false` |
| `class` | 应用类名 | `com.mitchellh.ghostty` |
| `x11-instance-name` | X11 实例名 | `ghostty` |

### 2.27 其他设置

| 选项 | 描述 | 默认值 |
|------|------|--------|
| `auto-update` | 自动更新：`off`/`check`/`download` | 未设置 |
| `auto-update-channel` | 更新频道：`stable`/`tip` | 匹配当前版本 |
| `async-backend` | 异步 IO 后端：`auto`/`epoll`/`io_uring` | `auto` |
| `app-notifications` | 应用内通知（仅 GTK） | `clipboard-copy,config-reload` |
| `desktop-notifications` | 桌面通知 | `true` |
| `progress-style` | 进度条样式 | `true` |
| `osc-color-report-format` | OSC 颜色报告格式：`none`/`8-bit`/`16-bit` | `16-bit` |
| `vt-kam-allowed` | 是否允许 KAM 模式 | `false` |
| `command-palette-entry` | 命令面板自定义条目 | 内置默认 |
| `config-file` | 额外配置文件 | — |
| `config-default-files` | 是否加载默认配置文件 | `true` |

---

## 3. 快捷键配置

### 3.1 基本语法

```ini
keybind = trigger=action
```

### 3.2 触发器（Trigger）

触发器由零个或多个修饰键和一个按键组成：

```ini
keybind = a=action                    # 单键
keybind = ctrl+a=action               # Ctrl + A
keybind = ctrl+shift+a=action         # Ctrl + Shift + A
```

**物理键码**（W3C 规范，不受键盘布局影响）：

```ini
keybind = KeyA=action                 # 物理A键
keybind = key_a=action                # 蛇形命名等价
```

**Unicode 码点**：

```ini
keybind = ctrl+ö=action              # 德语键盘上的 ö
```

### 3.3 修饰键

| 修饰键 | 别名 |
|--------|------|
| `shift` | — |
| `ctrl` | `control` |
| `alt` | `opt`, `option` |
| `super` | `cmd`, `command` |

> fn / Globe 键不支持作为修饰键。

### 3.4 触发器前缀

#### `all:` — 应用到所有终端表面

```ini
keybind = all:ctrl+a=action
```

#### `global:` — 全局快捷键（Ghostty 未聚焦时也生效）

```ini
keybind = global:cmd+backquote=toggle_quick_terminal
```

> 仅 macOS 支持。需要辅助功能权限。暗示 `all:`。

#### `unconsumed:` — 不消耗输入

```ini
keybind = unconsumed:ctrl+a=reload_config
```

按键同时触发操作并发送到终端程序。

#### `performable:` — 仅在操作可执行时消耗输入

```ini
keybind = performable:ctrl+c=copy_to_clipboard
```

### 3.5 按键序列（Leader Key）

用 `>` 分隔多个按键，实现类似 tmux 的 Leader Key：

```ini
keybind = ctrl+a>n=new_window
keybind = ctrl+a>t=new_tab
keybind = ctrl+a>\=new_split:right
```

**注意：** CLI 使用时需引号：`ghostty --keybind='ctrl+a>n=new_window'`

**特殊行为：**
- 无限等待下一个按键，无超时
- 如果序列前缀之前已绑定，序列会覆盖之前的绑定
- 序列不支持 `global:` 或 `all:` 前缀

### 3.6 链式操作

从 1.3.0 开始，一个快捷键可以绑定多个操作：

```ini
keybind = ctrl+a=new_window
keybind = chain=goto_split:left
keybind = chain=toggle_fullscreen
```

### 3.7 键表（Key Tables）

从 1.3.0 开始，支持模态键盘输入：

```ini
# 定义键表
copy_mode/ctrl+a=action          # copy_mode 表中的绑定
copy_mode/                       # 清除并重置表

# 激活/停用键表
keybind = ctrl+x=activate_key_table:copy_mode
keybind = escape=deactivate_key_table
```

### 3.8 特殊操作

| 操作 | 描述 |
|------|------|
| `ignore` | 忽略按键 |
| `unbind` | 解除绑定，按键发送到子程序 |
| `keybind=clear` | 清除所有快捷键 |

### 3.9 catch_all

匹配任何未绑定的按键：

```ini
keybind = ctrl+catch_all=ignore   # 忽略所有未绑定的 Ctrl 组合
```

### 3.10 默认快捷键

| macOS | Linux | 操作 |
|-------|-------|------|
| `cmd+,` | — | 打开配置 |
| `cmd+shift+,` | `ctrl+shift+,` | 重新加载配置 |
| `cmd+c` | `ctrl+shift+c` | 复制 |
| `cmd+v` | `ctrl+shift+v` | 粘贴 |
| `cmd+=` / `cmd++` | `ctrl++` / `ctrl+=` | 增大字体 |
| `cmd+-` | `ctrl+-` | 减小字体 |
| `cmd+0` | `ctrl+0` | 重置字体 |
| `cmd+n` | `ctrl+shift+n` | 新建窗口 |
| `cmd+t` | `ctrl+shift+t` | 新建标签 |
| `cmd+w` | `ctrl+shift+w` | 关闭表面 |
| `cmd+enter` | `f11` | 切换全屏 |
| `cmd+d` | — | 右分割 |
| `cmd+shift+d` | — | 下分割 |
| `cmd+]` / `cmd+[` | — | 下/上一个分割 |
| `cmd+f` | `ctrl+shift+f` | 搜索 |
| `cmd+k` | — | 清屏 |
| `cmd+q` | — | 退出 |

---

## 4. 快捷键操作参考（按功能分类）

### 4.1 窗口管理

| 操作 | 描述 | 参数 |
|------|------|------|
| `new_window` | 新建窗口 | — |
| `close_window` | 关闭窗口 | — |
| `close_all_windows` | 关闭所有窗口（已废弃，用 `all:close_window`） | — |
| `toggle_fullscreen` | 切换全屏 | — |
| `toggle_maximize` | 切换最大化（仅 Linux） | — |
| `toggle_window_decorations` | 切换窗口装饰（仅 Linux） | — |
| `toggle_window_float_on_top` | 切换置顶（仅 macOS） | — |
| `toggle_visibility` | 显示/隐藏所有窗口（仅 macOS） | — |
| `reset_window_size` | 重置窗口大小（仅 macOS） | — |
| `goto_window` | 切换窗口 | `previous`/`next` |

### 4.2 标签管理

| 操作 | 描述 | 参数 |
|------|------|------|
| `new_tab` | 新建标签 | — |
| `close_tab` | 关闭标签 | `this`/`other`/`right` |
| `previous_tab` | 上一个标签 | — |
| `next_tab` | 下一个标签 | — |
| `last_tab` | 最后一个标签 | — |
| `goto_tab` | 跳转到标签 | 索引（从 1 开始） |
| `move_tab` | 移动标签 | 偏移量（正/负） |
| `toggle_tab_overview` | 标签概览（仅 Linux） | — |
| `prompt_tab_title` | 提示修改标签标题 | — |
| `set_tab_title` | 设置标签标题 | 标题文本 |

### 4.3 分割管理

| 操作 | 描述 | 参数 |
|------|------|------|
| `new_split` | 新建分割 | `right`/`down`/`left`/`up`/`auto` |
| `goto_split` | 跳转到分割 | `left`/`right`/`up`/`down`/`previous`/`next` |
| `toggle_split_zoom` | 切换分割缩放 | — |
| `resize_split` | 调整分割大小 | `方向,像素` 如 `up,10` |
| `equalize_splits` | 均等分割大小 | — |

### 4.4 滚动操作

| 操作 | 描述 | 参数 |
|------|------|------|
| `scroll_to_top` | 滚到顶部 | — |
| `scroll_to_bottom` | 滚到底部 | — |
| `scroll_to_selection` | 滚到选中处 | — |
| `scroll_to_row` | 滚到指定行 | 行号（从 0 开始） |
| `scroll_page_up` | 上翻一页 | — |
| `scroll_page_down` | 下翻一页 | — |
| `scroll_page_fractional` | 按分数翻页 | 正数向下，负数向上 |
| `scroll_page_lines` | 按行数滚动 | 正数向下，负数向上 |
| `jump_to_prompt` | 跳转到提示符 | 正/负数（前/后） |

### 4.5 复制粘贴

| 操作 | 描述 | 参数 |
|------|------|------|
| `copy_to_clipboard` | 复制到剪贴板 | `plain`/`html`/`vt`/`mixed` |
| `paste_from_clipboard` | 从剪贴板粘贴 | — |
| `paste_from_selection` | 从选择剪贴板粘贴 | — |
| `copy_url_to_clipboard` | 复制光标下 URL | — |
| `copy_title_to_clipboard` | 复制终端标题 | — |
| `select_all` | 全选 | — |
| `adjust_selection` | 调整选择范围 | `left`/`right`/`up`/`down`/`page_up`/`page_down`/`home`/`end`/`beginning_of_line`/`end_of_line` |

### 4.6 搜索

| 操作 | 描述 | 参数 |
|------|------|------|
| `start_search` | 开始搜索 | — |
| `end_search` | 结束搜索 | — |
| `search` | 搜索指定文本 | 搜索文本 |
| `search_selection` | 搜索选中内容 | — |
| `navigate_search` | 导航搜索结果 | `next`/`previous` |

### 4.7 字体控制

| 操作 | 描述 | 参数 |
|------|------|------|
| `increase_font_size` | 增大字体 | 磅数（如 `1.5`） |
| `decrease_font_size` | 减小字体 | 磅数（如 `1.5`） |
| `reset_font_size` | 重置字体大小 | — |
| `set_font_size` | 设置字体大小 | 磅数（如 `14.5`） |

### 4.8 文本发送

| 操作 | 描述 | 参数 |
|------|------|------|
| `text:text` | 发送文本（Zig 字面量） | 如 `\x15` 发送 Ctrl-U |
| `csi:text` | 发送 CSI 序列 | 如 `A` 发送光标上移 |
| `esc:text` | 发送 ESC 序列 | 如 `d` 删除右边单词 |
| `cursor_key` | 发送光标键数据 | — |

### 4.9 终端操作

| 操作 | 描述 | 参数 |
|------|------|------|
| `reset` | 重置终端 | — |
| `clear_screen` | 清屏和回滚 | — |
| `inspector` | 检查器 | `toggle`/`show`/`hide` |
| `toggle_readonly` | 切换只读模式 | — |
| `toggle_mouse_reporting` | 切换鼠标报告 | — |
| `toggle_secure_input` | 切换安全输入（仅 macOS） | — |
| `toggle_background_opacity` | 切换背景透明度（仅 macOS） | — |

### 4.10 文件操作

| 操作 | 描述 | 参数 |
|------|------|------|
| `write_scrollback_file` | 写回滚到文件 | `copy`/`paste`/`open` |
| `write_screen_file` | 写屏幕到文件 | `copy`/`paste`/`open` |
| `write_selection_file` | 写选中内容到文件 | `copy`/`paste`/`open` |

### 4.11 快速终端

| 操作 | 描述 | 参数 |
|------|------|------|
| `toggle_quick_terminal` | 切换快速终端 | — |

### 4.12 其他

| 操作 | 描述 | 参数 |
|------|------|------|
| `open_config` | 打开配置文件 | — |
| `reload_config` | 重新加载配置 | — |
| `close_surface` | 关闭当前表面 | — |
| `quit` | 退出应用 | — |
| `undo` | 撤销（仅 macOS） | — |
| `redo` | 重做（仅 macOS） | — |
| `check_for_updates` | 检查更新（仅 macOS） | — |
| `toggle_command_palette` | 命令面板 | — |
| `show_gtk_inspector` | GTK 检查器 | — |
| `show_on_screen_keyboard` | 屏幕键盘（仅 Linux） | — |
| `prompt_surface_title` | 提示修改终端标题 | — |
| `set_surface_title` | 设置终端标题 | 标题文本 |
| `end_key_sequence` | 结束按键序列 | — |
| `activate_key_table` | 激活键表 | 表名 |
| `activate_key_table_once` | 单次激活键表 | 表名 |
| `deactivate_key_table` | 停用键表 | — |
| `crash` | 崩溃（调试用） | `main`/`render` |

---

## 5. 我的配置说明

### 5.1 配置文件结构

```
ghostty/
├── auto/
│   └── theme.ghostty       # 自动生成的主题（theme = Arcoiris）
├── config                  # 主配置文件
├── config.default          # 默认配置参考（完整注释）
└── README.md               # 本文档
```

### 5.2 当前配置解读

```ini
# 重新加载配置：cmd+shift+, (macOS) / ctrl+shift+, (Linux)

# 字体：Maple Mono NF CN（支持中文和 Nerd Font 图标），18pt
font-family = "Maple Mono NF CN"
font-family-bold = bold
font-size = 18

# 主题：Ayu
theme = Ayu

# 窗口：默认全屏
fullscreen = true

# 滚动：10万行历史
scrollback-limit = 100000

# 自动更新和终端类型
auto-update = download
term = xterm-256color
```

### 5.3 快捷键系统：Ctrl+A Leader Key

我使用 `Ctrl+A` 作为领导者键（类似 tmux），所有操作都通过两步完成：

```
Ctrl+A → 功能键
```

#### 滚动

| 快捷键 | 操作 |
|--------|------|
| `Ctrl+A → [` | 上翻一页 |
| `Ctrl+A → ]` | 下翻一页 |
| `Ctrl+A → ↑` | 滚到顶部 |
| `Ctrl+A → ↓` | 滚到底部 |

#### 分割

| 快捷键 | 操作 |
|--------|------|
| `Ctrl+A → \` | 右分割 |
| `Ctrl+A → -` | 下分割 |
| `Ctrl+A → =` | 均等分割大小 |

#### 分割导航（Vim 风格）

| 快捷键 | 操作 |
|--------|------|
| `Ctrl+A → h` | 左分割 |
| `Ctrl+A → l` | 右分割 |
| `Ctrl+A → k` | 上分割 |
| `Ctrl+A → j` | 下分割 |

#### 分割调整（Ctrl+A → r 进入调整模式）

| 快捷键 | 操作 |
|--------|------|
| `Ctrl+A → r → h` | 向左调整 |
| `Ctrl+A → r → l` | 向右调整 |
| `Ctrl+A → r → k` | 向上调整 |
| `Ctrl+A → r → j` | 向下调整 |
| `Ctrl+A → r → Esc` | 退出调整模式 |

#### 标签管理

| 快捷键 | 操作 |
|--------|------|
| `Ctrl+A → t` | 新建标签 |
| `Ctrl+A → n` | 下一个标签 |
| `Ctrl+A → p` | 上一个标签 |
| `Ctrl+A → 1-9` | 跳转到第 N 个标签 |

#### 字体大小

| 快捷键 | 操作 |
|--------|------|
| `Ctrl+A → +` | 增大字体 |
| `Ctrl+A → -` | 减小字体 |
| `Ctrl+A → 0` | 重置字体 |

#### 其他

| 快捷键 | 操作 |
|--------|------|
| `Ctrl+A → x` | 关闭当前表面 |
| `Ctrl+A → q` | 关闭窗口 |
| `Ctrl+A → f` | 切换全屏 |
| `Ctrl+A → i` | 切换检查器 |
| `Ctrl+A → v` | 进入复制模式 |

---

## 6. 配置示例和模板

### 6.1 最小配置

```ini
# 最小化配置，适合快速上手
font-size = 14
theme = Catppuccin Mocha
```

### 6.2 开发者配置

```ini
# 开发者友好配置
font-family = "JetBrains Mono"
font-size = 15
theme = Dracula
scrollback-limit = 100000
copy-on-select = true

# Shell 集成
shell-integration = detect
shell-integration-features = cursor,sudo,title,ssh-env,ssh-terminfo,path
```

### 6.3 透明背景 + 模糊

```ini
# macOS 透明背景效果
background-opacity = 0.85
background-blur = 20
```

### 6.4 Vim 风格分割管理

```ini
# Leader Key: Ctrl+A
# 类似 tmux 的操作方式

# 分割
keybind = ctrl+a>backslash=new_split:right
keybind = ctrl+a>minus=new_split:down

# Vim 风格导航
keybind = ctrl+a>h=goto_split:left
keybind = ctrl+a>j=goto_split:down
keybind = ctrl+a>k=goto_split:up
keybind = ctrl+a>l=goto_split:right

# 调整大小
keybind = ctrl+a>r>h=resize_split:left,10
keybind = ctrl+a>r>l=resize_split:right,10
keybind = ctrl+a>r>k=resize_split:up,10
keybind = ctrl+a>r>j=resize_split:down,10
keybind = ctrl+a>r>escape=unbind
```

### 6.5 多语言支持

```ini
# 中日韩字体支持
font-family = "JetBrains Mono"
font-family = "Noto Sans CJK SC"
font-size = 14
```

### 6.6 全局快速终端

```ini
# 从任何地方呼出终端（仅 macOS）
keybind = global:cmd+backquote=toggle_quick_terminal
quick-terminal-position = top
quick-terminal-animation-duration = 0.15
```

### 6.7 生产力配置

```ini
# 最大化生产力的配置
font-family = "Maple Mono NF CN"
font-size = 16
theme = Ayu
fullscreen = true
scrollback-limit = 100000

# 复制优化
copy-on-select = true
clipboard-paste-protection = true

# 搜索
keybind = ctrl+shift+f=start_search
keybind = ctrl+f=search_selection

# 快速标签切换
keybind = alt+1=goto_tab:1
keybind = alt+2=goto_tab:2
keybind = alt+3=goto_tab:3
```

### 6.8 禁用连字

```ini
# 禁用编程连字
font-feature = -calt
```

### 6.9 自定义 URL 处理

```ini
# 关闭默认 URL 匹配
link-url = false
```

---

## 7. 与其他终端的对比

### 7.1 Ghostty vs iTerm2（macOS）

| 特性 | Ghostty | iTerm2 |
|------|---------|--------|
| 渲染引擎 | 原生 GPU（Metal） | 原生 GPU（Metal） |
| 配置方式 | 文本配置 | GUI 偏好设置 + 文本 |
| GPU 加速 | 是 | 是 |
| 分割管理 | 内置 | 内置 |
| 标签管理 | 内置 | 内置 |
| Shell 集成 | 自动检测 | Shell 脚本 |
| 快速终端 | 内置（下拉式） | 需第三方 |
| 自定义着色器 | GLSL 支持 | 不支持 |
| 原生 UI | 是（SwiftUI/AppKit） | 是（Cocoa） |
| 内存使用 | 较低 | 较高 |
| 启动速度 | 快 | 较慢 |
| 主题数量 | 100+ 内置 | 可导入 |
| 领导者键 | 原生支持 | 不支持 |
| 键表模式 | 支持 | 不支持 |
| 价格 | 免费开源 | 免费开源 |
| 平台 | macOS + Linux | 仅 macOS |

**从 iTerm2 迁移建议：**
- Ghostty 使用文本配置而非 GUI，需要手动转换设置
- 大部分 iTerm2 的快捷键习惯可以通过自定义 keybind 保留
- Shell 集成方式不同，Ghostty 使用自动检测

### 7.2 Ghostty vs Alacritty

| 特性 | Ghostty | Alacritty |
|------|---------|-----------|
| 渲染引擎 | 原生 GPU | OpenGL/Vulkan |
| 配置方式 | 文本配置 | TOML 文件 |
| GPU 加速 | 是 | 是 |
| 分割管理 | 内置 | 需 tmux |
| 标签管理 | 内置 | 需 tmux |
| Shell 集成 | 自动 | 无 |
| 自定义着色器 | 支持 | 不支持 |
| 字体回退 | 多重回退 | 单一回退 |
| Nerd Fonts | 内置 | 需手动安装 |
| 领导者键 | 原生支持 | 支持（通过 mode） |
| 配置热重载 | 支持 | 支持 |
| 回滚缓冲 | 内置 | 有限 |
| URL 点击 | 内置 | 内置 |
| 搜索功能 | 内置 | 内置 |
| 平台 | macOS + Linux | macOS + Linux + Windows + BSD |
| 默认终端类型 | xterm-ghostty | xterm-256color |

**从 Alacritty 迁移建议：**
- 配置格式不同（Ghostty 用 `key = value`，Alacritty 用 TOML）
- Ghostty 内置分割和标签，无需 tmux
- 大多数 Alacritty 功能在 Ghostty 中都有对应

### 7.3 Ghostty vs Kitty

| 特性 | Ghostty | Kitty |
|------|---------|-------|
| 渲染引擎 | 原生 GPU | OpenGL |
| 配置方式 | 文本配置 | 文本配置 |
| GPU 加速 | 是 | 是 |
| 分割管理 | 内置 | 内置 |
| 标签管理 | 内置 | 内置 |
| 图像协议 | Kitty 协议 | Kitty 协议 |
| Shell 集成 | 自动检测 | Shell 脚本 |
| 自定义着色器 | 支持 | 支持 |
| 性能 | 极高 | 极高 |
| macOS 原生体验 | 更好 | 一般 |
| Wayland 支持 | 好 | 好 |
| 平台 | macOS + Linux | macOS + Linux |
| 编程语言 | Zig | Python + C |
| 二进制大小 | 较小 | 较大 |

**从 Kitty 迁移建议：**
- 配置语法相似，但键名不同
- Kitty 的 `kitten` 功能在 Ghostty 中可能需要不同的实现方式
- 图像协议兼容，大部分 Kitty 图形程序可直接使用

### 7.4 Ghostty vs WezTerm

| 特性 | Ghostty | WezTerm |
|------|---------|---------|
| 渲染引擎 | 原生 GPU | OpenGL/EGL |
| 配置方式 | 文本配置 | Lua 脚本 |
| GPU 加速 | 是 | 是 |
| 分割管理 | 内置 | 内置 |
| 标签管理 | 内置 | 内置 |
| 脚本化 | 有限（配置文件） | 完全可编程（Lua） |
| Shell 集成 | 自动 | 手动 |
| 多路复用 | 内置 | 内置（mux domain） |
| 远程终端 | 有限 | 支持（SSH multiplexing） |
| 平台 | macOS + Linux | macOS + Linux + Windows |
| 配置复杂度 | 低 | 中高 |

---

## 8. 实用技巧和最佳实践

### 8.1 常用 CLI 命令

```sh
# 查看所有可用字体
ghostty +list-fonts

# 查看所有可用主题
ghostty +list-themes

# 查看所有可用操作
ghostty +list-actions

# 查看当前配置（含文档）
ghostty +show-config --default --docs

# 查看当前快捷键
ghostty +list-keybinds --default

# 查看版本信息
ghostty +version

# 使用 -e 执行特定命令
ghostty -e fish
ghostty -e nvim README.md
```

### 8.2 性能优化

1. **减少回滚缓冲区**：`scrollback-limit = 10000`
2. **禁用着色器动画**：`custom-shader-animation = false`
3. **关闭垂直同步**（macOS，需注意风险）：`window-vsync = false`
4. **减少背景模糊**：不使用 `background-blur`

### 8.3 常见问题解决

**问题：字体显示不正确**
```ini
# 确认字体可用
ghostty +list-fonts | grep "字体名"

# 设置回退字体
font-family = "主字体"
font-family = "回退字体"
```

**问题：SSH 后颜色异常**
```ini
# 启用 SSH terminfo 安装
shell-integration-features = cursor,title,ssh-env,ssh-terminfo,path
```

**问题：Option 键无法作为 Alt**
```ini
# macOS 设置 Option 作为 Alt
macos-option-as-alt = true
```

**问题：中文显示方框**
```ini
# 设置中文字体回退
font-family = "JetBrains Mono"
font-family = "Noto Sans CJK SC"
```

**问题：终端重置**
```
# 使用快捷键或命令重置终端
# 操作：reset
# 或者在命令面板中选择 "Reset Terminal"
```

### 8.4 调试技巧

```sh
# 查看日志
log stream --process-name ghostty --level debug

# 打开检查器
# 快捷键：Ctrl+A → i（我的配置）
# 或命令面板中选择 "Toggle Inspector"

# GTK 调试
env GTK_DEBUG=interactive ghostty
```

### 8.5 推荐主题

| 主题 | 风格 | 适用场景 |
|------|------|----------|
| Catppuccin Mocha | 深色，暖色调 | 通用开发 |
| Dracula | 深色，高对比 | 通用开发 |
| Ayu | 深色/浅色 | 舒适阅读 |
| Gruvbox Dark | 深色，暖色调 | Vim 用户 |
| Tokyo Night | 深色，冷色调 | 现代开发 |
| Nord | 深色，冷色调 | 长时间编码 |
| Solarized Dark | 经典深色 | 经典主题爱好者 |
| Rose Pine | 深色，优雅 | 极简主义 |
| One Dark | 深色 | VS Code 用户 |

### 8.6 配置管理建议

1. **版本控制**：将配置文件放入 Git 管理
2. **模块化**：使用 `config-file` 拆分不同用途的配置
3. **注释**：为每个配置段添加注释说明用途
4. **备份**：定期备份配置文件
5. **渐进配置**：从默认配置开始，逐步添加自定义设置

---

## 参考资料

- [Ghostty 官方文档](https://ghostty.org/docs)
- [配置选项参考](https://ghostty.org/docs/config/reference)
- [快捷键配置](https://ghostty.org/docs/config/keybind)
- [快捷键序列](https://ghostty.org/docs/config/keybind/sequence)
- [快捷键操作参考](https://ghostty.org/docs/config/keybind/reference)
- [Ghostty GitHub](https://github.com/ghostty-org/ghostty)
- [Ghostty Discord](https://discord.gg/ghostty)

---

*最后更新：2026年5月11日*
*文档版本：基于 Ghostty 1.3.0+*
