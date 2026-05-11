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

默认使用 `themes/tmux2k.conf`。切换到 Catppuccin 时：`tmux.conf` 中的 `source-file ~/.config/tmux/themes/catppuccin.conf`，以及 **`run tpm` 之后** 对 `themes/catppuccin-status-post-tpm.conf` 的 `source-file`，两处需同时启用（换用 tmux2k 时对两处一齐注释）。保存后在 tmux 内执行 `prefix`+`I` 安装插件；大版本升级插件后可尝试 `killall tmux` 再起会话。

### Catppuccin v2：根因（为何不生效）

`catppuccin/tmux` 在 v2 后与旧配置不兼容，典型表现是状态栏上的时间、路径等「怎么改都不出现」：

1. **旧选项被废弃**：`@catppuccin_status_modules_right` 这类「用字符串列出右侧模块」的方式在 v2 中不再生效；主题只负责注册各模块对应的用户选项（如 `@catppuccin_status_date_time` 等），**不会**再根据旧列表自动拼装 `status-right`。
2. **v2 需显式拼装状态栏**：须在加载主题之后，用 tmux 自带的 `status-left` / `status-right`，按顺序接入 `#{E:@catppuccin_status_directory}`、`#{E:@catppuccin_status_session}`、`#{E:@catppuccin_status_date_time}` 等占位符（详见上游 [status-line 文档](https://github.com/catppuccin/tmux/blob/main/docs/reference/status-line.md)）。
3. **顺序要求**：以 `@` 开头的 Catppuccin 选项在 **`run tpm`（插件实际执行 `catppuccin.tmux`）之前** 设置；普通 tmux 选项如 `status-right`、`status-left` 须在 **主题加载完成之后** 设置，否则要么引用未就绪，要么与官方说明不一致（参考上游 [Troubleshooting](https://github.com/catppuccin/tmux/blob/main/docs/guides/troubleshooting.md)）。因此本仓库把状态栏拼装单独放在 `themes/catppuccin-status-post-tpm.conf`，并在 `run tpm` 之后再 `source-file`。

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
| `Prefix` + `h/j/k/l` | 面板导航 (左/下/上/右) |
| `Prefix` + `H/J/K/L` | 调整面板大小 |
| `Prefix` + `>` / `<` | 交换面板 |
| `Prefix` + `z` | 面板全屏切换 |

## 窗口 (Window)

| 快捷键 | 说明 |
|--------|------|
| `Prefix` + `Ctrl+h` | 上一个窗口 |
| `Prefix` + `Ctrl+l` | 下一个窗口 |
| `Prefix` + `Ctrl+Shift+H` | 窗口左移 |
| `Prefix` + `Ctrl+Shift+L` | 窗口右移 |
| `Prefix` + `Tab` | 切换到上次活跃窗口 |

## 其他

| 快捷键 | 说明 |
|--------|------|
| `Prefix` + `b` | 列出粘贴缓冲区 |
| `Prefix` + `p` | 粘贴 |
| `Prefix` + `P` | 选择缓冲区粘贴 |
