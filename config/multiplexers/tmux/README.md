# Init
```shell
make install
```

# Install Plugins
```shell
# enter tmux
tmux
# install plugins
<prefix>+I  # prefix: Ctrl+Space
```

## 主题

默认使用 `themes/tmux2k.conf`。切换到 Catppuccin 时在 `tmux.conf` 中：**启用** `source-file ~/.config/tmux/themes/catppuccin.conf`，以及 **`run tpm` 之后** 的 `source-file ~/.config/tmux/themes/catppuccin-status-post-tpm.conf`。换用 tmux2k 时对上述 **两行一齐注释**，并改用 `themes/tmux2k.conf`。保存后在 tmux 内执行 `prefix`+`I` 安装插件；大版本升级插件后可尝试 `killall tmux` 再起会话。

### Catppuccin v2：根因（为何不生效）

`catppuccin/tmux` 在 v2 后与旧配置不兼容，典型表现是状态栏上的时间、路径等「怎么改都不出现」：

1. **旧选项被废弃**：`@catppuccin_status_modules_right` 这类「用字符串列出右侧模块」的方式在 v2 中不再生效；主题只负责注册各模块对应的用户选项（如 `@catppuccin_status_date_time` 等），**不会**再根据旧列表自动拼装 `status-right`。
2. **v2 需显式拼装状态栏**：须在加载主题之后，用 tmux 自带的 `status-left` / `status-right`，按顺序接入 `#{E:@catppuccin_status_directory}`、`#{E:@catppuccin_status_session}`、`#{E:@catppuccin_status_date_time}` 等占位符（详见上游 [status-line 文档](https://github.com/catppuccin/tmux/blob/main/docs/reference/status-line.md)）。
3. **顺序要求**：在 `catppuccin.conf` 里以 `@` 开头的 Catppuccin 选项必须在 **`run tpm` 之前** 写入配置（TPM 在这一步执行各插件的入口脚本，包括主题的 `catppuccin.tmux`）。`status-right` / `status-left` 等普通 tmux 选项须在 **上述脚本跑完之后** 再设置（参考上游 [Troubleshooting](https://github.com/catppuccin/tmux/blob/main/docs/guides/troubleshooting.md)）。因此本仓库把状态栏拼装放在 `themes/catppuccin-status-post-tpm.conf`，并在 `run tpm` **之后** `source-file`。

# Keybindings

> Prefix: `Ctrl+Space`

## Copy Mode

| 快捷键 | 说明 |
|--------|------|
| `Prefix` + `Enter` | 进入 copy mode |
| `v` | 开始选择 |
| `Ctrl+v` | 矩形选择 |
| `y` | 复制并退出 |
| `Escape` | 取消 |
| `H` | 跳到行首 |
| `L` | 跳到行尾 |

## 面板 (Pane)

| 快捷键 | 说明 |
|--------|------|
| `Prefix` + `-` | 水平分割 |
| `Prefix` + `\` | 垂直分割 |
| `Prefix` + `o` | 右侧 25% 打开 opencode |
| `Prefix` + `e` | 右侧 25% 打开 claude |
| `Prefix` + `u` | 右侧 25% 打开 cursor-agent |
| `Prefix` + `v` | 右侧 25% 打开 kimi |
| `Prefix` + `p` | 右侧 25% 打开 pi |
| `Prefix` + `h/j/k/l` | 面板导航 (左/下/上/右) |
| `Prefix` + `H/J/K/L` | 调整面板大小 |
| `Prefix` + `>` / `<` | 交换面板 |
| `Prefix` + `z` | 面板全屏切换 |
| `Prefix` + `x` | 关闭面板 (默认) |
| `Prefix` + `{` / `}` | 面板交换位置 (默认) |
| `Prefix` + `;` | 切换到上一个面板 (默认) |
| `Prefix` + `!` | 面板独立为新窗口 (默认) |
| `Prefix` + `space` | 切换布局 (默认) |

## 窗口 (Window)

| 快捷键 | 说明 |
|--------|------|
| `Prefix` + `Ctrl+h` | 上一个窗口 |
| `Prefix` + `Ctrl+l` | 下一个窗口 |
| `Prefix` + `Ctrl+Shift+H` | 窗口左移 |
| `Prefix` + `Ctrl+Shift+L` | 窗口右移 |
| `Prefix` + `Tab` | 切换到上次活跃窗口 |
| `Prefix` + `c` | 新建窗口 (默认) |
| `Prefix` + `n` / `p` | 下/上一个窗口 (默认) |
| `Prefix` + `&` | 关闭窗口 (默认) |
| `Prefix` + `,` | 重命名窗口 (默认) |
| `Prefix` + `f` | 搜索窗口 (默认) |
| `Prefix` + `w` | 窗口列表 (默认) |
| `Prefix` + `0-9` | 跳转到指定窗口 (默认) |

## 其他

| 快捷键 | 说明 |
|--------|------|
| `Prefix` + `b` | 列出粘贴缓冲区 |
| `Prefix` + `p` | 粘贴 |
| `Prefix` + `P` | 选择缓冲区粘贴 |
| `Prefix` + `d` | 断开连接 (默认) |
| `Prefix` + `$` | 重命名会话 (默认) |
| `Prefix` + `s` | 选择会话 (默认) |
| `Prefix` + `:` | 进入命令模式 (默认) |
| `Prefix` + `?` | 列出所有快捷键 (默认) |
| `Prefix` + `r` | 刷新终端状态 (默认) |

## 未使用快捷键

Prefix (`Ctrl+Space`) 下尚未被占用的按键，可直接用于添加新绑定：

| 按键 | 说明 |
|------|------|
| `a` | 空闲 |
| `g` | 空闲 |
| `y` | 空闲 |

> **说明**：tmux 默认会有很多快捷键（如 `c` 新建窗口、`x` 关闭面板等），本仓库只显式覆盖了部分。未覆盖的 tmux 默认绑定仍然生效，因此上述「空闲」列表已排除了所有默认快捷键。若需要更多空闲按键，可在 `tmux.conf` 中 `unbind` 不需要的默认绑定。
