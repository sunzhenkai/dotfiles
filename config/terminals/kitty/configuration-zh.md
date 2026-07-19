# Kitty 配置选项速查（中文摘要）

> **版本说明**：编写本文时以 [官方 kitty.conf 说明](https://sw.kovidgoyal.net/kitty/conf/) 与 [可映射动作](https://sw.kovidgoyal.net/kitty/actions/) 为准；**完整选项、默认值与边界情况请务必查阅官方文档**。  
> 请在本地运行 **`kitty --version`** 记录你当前环境；不同版本功能可能略有差异。

---

## 1. 基础

| 主题 | 说明 |
|------|------|
| 配置文件路径 | 通常为 `~/.config/kitty/kitty.conf`，也可用 `kitty --config` 或环境变量 `KITTY_CONFIG_DIRECTORY`；见 [Invocation](https://sw.kovidgoyal.net/kitty/invocation/) |
| 注释与换行 | 行首 `#` 为注释；行尾 `\` 可续行 |
| `include` / `globinclude` | 拆分配置、按系统包含文件；见官方 [include](https://sw.kovidgoyal.net/kitty/conf/#include) |
| 重载配置 | 默认 **`Ctrl+Shift+F5`**（macOS 亦常见 **⌃+⌘+,**），或对进程发 **`SIGUSR1`**；见官方说明 |
| 编辑配置 | **`Ctrl+Shift+F2`**（macOS **⌘+,**） |
| 查看生效配置 | **`Ctrl+Shift+F6`** |

官方索引： [https://sw.kovidgoyal.net/kitty/conf/](https://sw.kovidgoyal.net/kitty/conf/)

---

## 2. 字体

| 选项 | 作用摘要 |
|------|-----------|
| `font_family` | 主字体；可变体可通过 `family="..." wght=800` 等形式指定 |
| `bold_font` / `italic_font` / `bold_italic_font` | 变体；常用 `auto` |
| `font_size` | 字号（点） |
| `symbol_map` | 指定 Unicode 区间到某字体，避免全靠 Nerd 合并字体 |
| `adjust_line_height` / `adjust_column_width` | 行高、列宽微调（若需） |

进阶：`kitten choose-fonts` 可视化选字体。见 [Fonts 段](https://sw.kovidgoyal.net/kitty/conf/#fonts)。

**本仓库示例（摘录）**

```conf
font_family      family="Maple Mono" wght=800
bold_font        auto
italic_font      auto
bold_italic_font auto
font_size 18.0
```

---

## 3. 颜色与主题

| 选项 | 作用摘要 |
|------|-----------|
| `foreground` / `background` | 前景/背景色 |
| `color0`–`color15` | 16 色 |
| `cursor` / `selection_*` | 光标与选择颜色 |
| `include` | 引入预置主题文件（本仓库使用 `include themes/Gruvbox-Light.conf`） |

见 [Colors](https://sw.kovidgoyal.net/kitty/conf/) 与主题文件内注释。

---

## 4. 滚动与滚动缓冲区

| 选项 | 作用摘要 |
|------|-----------|
| `scrollback_lines` | 保留行数；过大占用内存，官方建议超大历史用 pager/其它策略 |
| `scrollback_pager` | 查看历史的 pager 命令 |
| `wheel_scroll_multiplier` 等 | 滚轮/触控板倍率 |

见 [Scrollback](https://sw.kovidgoyal.net/kitty/conf/#scrollback)。

**本仓库**：`scrollback_lines 100000`。

**半页滚动**：本仓库通过 **`map` + `remote_control scroll-window`** 绑定到 `Ctrl+a` → `[` / `]`；语法与键位见 `kitty.conf` 与 `keybindings.md`。底层属 [Remote control](https://sw.kovidgoyal.net/kitty/remote-control/) 中的 `scroll-window`。

---

## 5. 鼠标

常见项：`url_style`、`open_url_with`、`detect_urls`、`mouse_hide_wait` 等。见 [Mouse](https://sw.kovidgoyal.net/kitty/conf/#mouse)。

---

## 6. 键盘与快捷键

| 选项/语法 | 作用摘要 |
|------------|-----------|
| `map` | 将按键绑定到动作；支持 **`combine`**、**多键序列**（`key1>key2`）、**模态模式**（`--new-mode` / `--mode`） |
| `kitty_mod` | 整组默认快捷键使用的前缀修饰键，默认常为 **`ctrl+shift`**；修改会影响大量默认 `kitty_mod+*` |
| `map_timeout` | 多键序列的超时（秒） |
| `mouse_map` | 鼠标动作 |
| `clear_all_shortcuts` | 清空所有默认快捷键（本仓库**未**启用，以免丢失自带绑定） |

详细语法见 [Making your keyboard dance](https://sw.kovidgoyal.net/kitty/mapping/)。

**本仓库 Leader 风格**（与 `kitty_mod` 无关）：使用 **`ctrl+a>h`** 等形式与 **`--new-mode`** 子模式，摘录：

```conf
map_timeout 2.0

map ctrl+a>h neighboring_window left
map --new-mode resize --timeout 5.0 ctrl+a>r
map --mode resize h resize_window narrower
```

---

## 7. 窗口、标签与 OS 窗口

包含：`new_tab`、`close_tab`、`macos_*` 系列等默认快捷键；配置项如 `tab_bar_style`、`tab_bar_min_tabs`、`window_padding_width`、`hide_window_decorations` 等。见 [Window layout](https://sw.kovidgoyal.net/kitty/conf/) 相关章节。

**本仓库**：`tab_bar_min_tabs 2`（仅一个标签时隐藏标签栏）。

---

## 8. 布局

| 选项 | 作用摘要 |
|------|-----------|
| `enabled_layouts` | 可用布局列表，首个为默认 |
| Splits | 通过 `launch --location=hsplit|vsplit|split` 等分割 |

见 [Arrange windows / Layouts](https://sw.kovidgoyal.net/kitty/layouts/)。

**本仓库**：`enabled_layouts splits`。

---

## 9. 高级功能

| 选项 | 作用摘要 |
|------|-----------|
| `allow_remote_control` | 允许远程控制；键位里 `map ... remote_control ...` **不依赖**此项，但其它 `kitten @` 场景需要按需开启 |
| `clipboard_control` | 剪贴板读写策略（Linux 上常见 `primary`） |
| `shell_integration` | Shell 集成（提示符跳转等） |
| `listen_on` | 套接字监听，供外部 `kitten @ --to` 使用 |

见 [Remote control](https://sw.kovidgoyal.net/kitty/remote-control/) 与 [Shell integration](https://sw.kovidgoyal.net/kitty/shell-integration/)。

**本仓库**：`allow_remote_control yes`、`copy_on_select yes`。

---

## 10. 本仓库配置摘录（与 `kitty.conf` 一致）

```conf
include themes/Gruvbox-Light.conf
enabled_layouts splits
tab_bar_min_tabs 2
scrollback_lines 100000
enable_audio_bell no
allow_remote_control yes
copy_on_select yes
clipboard_control write-clipboard write-primary read-clipboard read-primary
map_timeout 2.0
```

---

## 11. 故障排查

1. **配置报错 / 未生效**  
   - 使用 **`kitty --debug-config`** 查看加载与错误。  
   - 修改后 **`Ctrl+Shift+F5`** 重载；部分选项需重启 Kitty。  
   - 运行时 **`Ctrl+Shift+F6`** 查看当前生效配置。

2. **字体或图标异常**  
   - 运行 **`kitty +list-fonts`**（或 `kitten choose-fonts`）核对名称。  
   - 检查 `symbol_map` 区间是否覆盖对应 Unicode。  

3. **快捷键无效或异常**  
   - 冲突：与系统快捷键或其它应用抢占；可用 **`kitty --debug-input`** 排查。  
   - 多键序列：检查 **`map_timeout`** 是否过短。  
   - **`Ctrl+a` 前缀**：使用 shell/读行库时可能与「行首」等默认 **`Ctrl+a`** 行为竞争；若需可调整前缀或加条件映射（见官方 **conditional mappings**）。

4. **`remote_control scroll-window` 无效**  
   - 同一行 **`map` 后不要接 `#` 注释**（部分版本解析会把注释带入参数）。  
   - 升级 Kitty 或查阅 [Issue #6000](https://github.com/kovidgoyal/kitty/issues/6000) 一类兼容性说明。

---

## 12. OpenSpec 规格对照（`migrate-wezterm-to-kitty`）

| 规格文件 | 落实方式 |
|----------|-----------|
| `kitty-terminal-config/spec.md` | `kitty.conf`：单一文件、Gruvbox Light、字体、scrollback、splits、`allow_remote_control` / 剪贴板 / 静音铃等 |
| `kitty-keybindings/spec.md` | `ctrl+a>...` 序列、`--new-mode` resize / pane_nav、`show_scrollback`、`command_palette`；默认 Kitty 键位保留，见 `keybindings.md` |
| `kitty-docs/spec.md` | 本文按功能分节 + 官方链接 + 故障排查 |

**明确未实现 / 非目标**（见变更 `proposal.md` / `design.md`）：WezTerm 右侧状态栏、Lua 级自定义标签渲染、与 WezTerm 完全一致的「复制模式」矩形选区等。
