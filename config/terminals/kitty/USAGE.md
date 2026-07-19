# Kitty 使用说明

本文说明**如何用**本仓库中的 Kitty 配置，不涉及逐项配置字典（那部分见 [configuration-zh.md](configuration-zh.md)）或完整键位表（见 [keybindings.md](keybindings.md)）。

---

## 1. 你能得到什么

- **外观**：Gruvbox Light 主题、Maple Mono 约 18pt、较长的滚动历史（10 万行量级）。
- **操作习惯**：沿用原 WezTerm 里 **`Ctrl+a` 作为「前缀」** 的思路；在 Kitty 里体现为**先按 `Ctrl+a`，再按第二个键**（配置里写作 `ctrl+a>h` 这类**多键序列**）。
- **不移植**：WezTerm 里 Lua 写的标签栏箭头、右侧状态栏等未搬到 Kitty（见 [keybindings.md](keybindings.md) 底部对照表）。

---

## 2. 让 Kitty 读到这份配置

1. 已安装 [Kitty](https://sw.kovidgoyal.net/kitty/)。
2. 将本目录作为 **`~/.config/kitty`** 使用（任选其一）：
   - **符号链接**（适合本仓库直接当 dotfiles）：
     ```bash
     ln -sfn /你的/dotfiles/路径/kitty ~/.config/kitty
     ```
   - 或仅复制 / 合并 `kitty.conf` 等到 `~/.config/kitty/`。
3. **macOS**：本仓库包含 `macos-launch-services-cmdline`（内容为 `--start-as=fullscreen`）。从 **程序坞 / Spotlight / `open -a kitty`** 等 GUI 方式启动时，Kitty 会读取该文件并让**首个 OS 窗口以全屏打开**（见 [官方 FAQ](https://sw.kovidgoyal.net/kitty/faq/#how-do-i-specify-command-line-options-for-kitty-on-macos)）。在终端里直接执行 `kitty` **不会**读此文件；若也需要全屏，请使用 `kitty --start-as=fullscreen` 或自行 alias。
4. 首次启动或改完配置后，建议执行：
   ```bash
   kitty --debug-config
   ```
   无报错再正常打开 `kitty`。

---

## 3. 日常最简用法（前缀 `Ctrl+a`）

- **多键序列**：先松开 `Ctrl+a`，再按下一键（与「长按 `Ctrl+a` 再按别的」不是同一手势；习惯上与 WezTerm Leader 一致）。
- **超时**：未在超时时间内按完第二键，序列会取消；本仓库设置了 `map_timeout`（见 `kitty.conf`）。若总误触，可在 `kitty.conf` 里微调该值。
- **分栏**：`Ctrl+a` → `\`（左右）、`Ctrl+a` → `-`（上下）。
- **在窗格间跳**：`Ctrl+a` → `h` / `j` / `k` / `l`。
- **半页滚**：`Ctrl+a` → `[` 或 `]`。
- **在 pager 里看历史（替代 WezTerm 复制模式）**：`Ctrl+a` → `v`；退出一般按 `q`（具体以 pager 为准）。
- **命令面板**：`Ctrl+a` → `c`（或 Kitty 默认 `Ctrl+Shift+F3`）。
- **macOS 全屏**：`⌘+↩` 切换全屏；新建窗格可用 `Ctrl+Shift+↩` 或上表 `Ctrl+a` 分栏（见 [keybindings.md](keybindings.md)）。

**子模式**（与旧 WezTerm 的 Key Table 类似）：

- **改大小**：`Ctrl+a` → `r` 进入 resize 模式，再用方向键或 `h` / `j` / `k` / `l` 调整；`Esc`（配置里映射为 `esc`）退出。
- **短时只用于切窗格**：`Ctrl+a` → `p`，约 1 秒内用方向键或 `h` / `j` / `k` / `l`；`Esc` 退出。

更全的键位与默认 `Ctrl+Shift+…` 补充见 [keybindings.md](keybindings.md)。

---

## 4. 改配置以后怎么做

1. 编辑 `~/.config/kitty/kitty.conf`（或本仓库中同名文件）。
2. 在 Kitty 窗口里 **`Ctrl+Shift+F5`** 重载（macOS 亦常见 **⌃⌘,**）。
3. 若某项要求重启 Kitty，以 [官方说明](https://sw.kovidgoyal.net/kitty/conf/) 为准。
4. 可用 **`Ctrl+Shift+F6`** 查看当前**实际生效**的配置，避免「改了文件但未加载」的困惑。

---

## 5. 与 shell / 编辑器里的 `Ctrl+a` 冲突时

- 读行库里 **`Ctrl+a` 常表示「行首」**（emacs 模式）。若你在按前缀时经常被应用抢走，可尝试：缩短或延长 `map_timeout`、换前缀（需改 `kitty.conf` 里所有 `ctrl+a>`）、或为特定程序配置条件映射（见 [官方 Keyboard mapping](https://sw.kovidgoyal.net/kitty/mapping/)）。

---

## 6. 文档与仓库指引

| 需求 | 打开 |
|------|------|
| 所有快捷键与 WezTerm 差异 | [keybindings.md](keybindings.md) |
| 常用配置项中文摘要、故障排查 | [configuration-zh.md](configuration-zh.md) |
| 目录说明、与官方手册入口 | [README.md](README.md) |
| 官方完整选项 | [https://sw.kovidgoyal.net/kitty/conf/](https://sw.kovidgoyal.net/kitty/conf/) |

---

## 7. 仍用 WezTerm 对照时

仓库中的 **`wezterm/`** 未删除；可与 `kitty/` 并行参照，逐步把肌肉记忆迁到 Kitty。
