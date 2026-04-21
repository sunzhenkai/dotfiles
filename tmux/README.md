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
