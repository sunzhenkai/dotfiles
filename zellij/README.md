# Zellij 使用说明

本目录下的 [`config.kdl`](config.kdl) 为本机 Zellij 配置；键位以该文件为准。以下为与当前配置一致的使用摘要。

## 外部资源

- [Awesome zellij resources](https://github.com/zellij-org/awesome-zellij?tab=readme-ov-file)

## 概念

Zellij 是终端里的会话/工作区管理器：一个**会话**里有多 **Tab**，每个 Tab 里有多 **Pane**（分屏）。可滚动回看、detach 后再 attach。与 tmux 类似，默认通过**模式（mode）**分层绑定快捷键，减少与前台程序抢键。

## 模式与进入方式

多数模式下可用 **Enter** 或 **Esc** 回到 Normal（见配置中 `shared_except "normal" "locked"`）。

| 模式 | 作用简述 | 进入快捷键 |
|------|----------|------------|
| Normal | 默认，字符交给当前 pane | （默认启动模式） |
| Locked | 几乎不拦截按键，适合全屏程序 | **Ctrl+g**（从 Normal 进入） |
| Pane | 分屏、焦点、关闭等 | **Ctrl+p** |
| Resize | 调整分割大小 | 见下文「Ctrl+n 与 unbind」 |
| Tab | 标签页切换、新建、重命名等 | **Ctrl+t** |
| Scroll | 滚动、搜索 scrollback | **Ctrl+s** |
| Move | 在布局中移动 pane | **Ctrl+h** |
| Session | 分离会话、打开内置插件 | **Ctrl+,**（逗号） |
| Tmux | tmux 风格前缀后再按子键 | **Ctrl+b** |

在 **Locked** 下按 **Ctrl+g** 回到 Normal。

## 全局快捷键（除 Locked 外）

- **Ctrl+g**：Normal ↔ Locked  
- **Ctrl+q**：退出 Zellij  
- **Alt+f**：切换浮动 pane  
- **Alt+n**：新建 pane  
- **Alt+i** / **Alt+o**：当前 Tab 左移 / 右移  
- **Alt+h** / **Alt+l**（或 **Alt+左** / **Alt+右**）：`MoveFocusOrTab`，在 pane 与相邻 Tab 间移动焦点  
- **Alt+j** / **Alt+k**（或 **Alt+下** / **Alt+上**）：焦点上下移动  
- **Alt+=** / **Alt++** / **Alt+-**：当前布局整体放大 / 缩小  
- **Alt+[** / **Alt+]**：上一套 / 下一套 swap layout  

## Pane 模式（Ctrl+p）

- **h j k l** 或方向键：移动焦点  
- **p**：在 pane 间切换焦点  
- **n**：新建 pane，并回到 Normal  
- **d** / **r**：向下 / 向右分屏，并回到 Normal  
- **x**：关闭当前 pane，并回到 Normal  
- **f**：当前 pane 全屏切换，并回到 Normal  
- **z**：pane 边框显示切换，并回到 Normal  
- **w**：浮动 pane 开关，并回到 Normal  
- **e**：嵌入 / 浮动切换，并回到 Normal  
- **c**：进入重命名 pane  
- **i**：固定 pane 切换，并回到 Normal  
- **Ctrl+p**：回到 Normal  

## Resize 模式

配置中 Resize 子模式内：**h j k l** 增大某侧；**H J K L** 减小对应侧；**+** / **=** 整体增大；**-** 整体减小；**Ctrl+n** 回到 Normal。

**注意：** `config.kdl` 末尾存在 `unbind "Ctrl n"`。若在你使用的 Zellij 版本中该语句会全局取消 **Ctrl+n**，则可能无法再用 **Ctrl+n** 从 Normal 进入 Resize（Resize 内退出键也可能受影响）。若行为与预期不符，请对照 [Zellij 文档](https://zellij.dev/documentation) 调整或删除该 `unbind`，或为 Resize 指定其它进入键。

## Tab 模式（Ctrl+t）

- **h** / **k** / **左** / **上**：上一 Tab  
- **l** / **j** / **右** / **下**：下一 Tab  
- **n**：新建 Tab，并回到 Normal  
- **x**：关闭当前 Tab，并回到 Normal  
- **r**：重命名 Tab  
- **1**–**9**：跳到对应编号 Tab，并回到 Normal  
- **Tab**：在最近使用的两个 Tab 间切换  
- **s**：同步输入到同组 Tab 开关，并回到 Normal  
- **b** / **]** / **[**：Break pane 相关，并回到 Normal  
- **Ctrl+t**：回到 Normal  

## Scroll 与搜索

**Scroll（Ctrl+s）**

- **j** / **k** 或 **下** / **上**：逐行滚动  
- **Ctrl+f** / **PageDown** / **右** / **l**：向下翻页  
- **Ctrl+b** / **PageUp** / **左** / **h**：向上翻页  
- **d** / **u**：半页下 / 半页上  
- **s**：进入搜索输入（EnterSearch）  
- **e**：用外部编辑器编辑 scrollback（当前配置为 **nvim**，见 `scrollback_editor`）  
- **Ctrl+c**：滚到底并回到 Normal  
- **Ctrl+s**：回到 Normal  

**Search / EnterSearch**：在对应子模式中 **n** / **p** 查找下/上一处；**c** / **w** / **o** 切换大小写、环绕、整词等选项（详见 `config.kdl` 中 `search` 块）。

## Move 模式（Ctrl+h）

**h j k l** 或方向键移动 pane；**n** / **Tab**、**p** 在布局中前后移动 pane；**Ctrl+h** 回到 Normal。

## Session 模式（Ctrl+,）

- **d**：detach 当前会话  
- **Ctrl+s**：进入 Scroll  
- **w**：浮动打开 session-manager  
- **c**：浮动打开 configuration  
- **p**：浮动打开 plugin-manager  
- **a**：浮动打开 about  
- **Ctrl+,**：回到 Normal  

## Tmux 模式（Ctrl+b）

先按 **Ctrl+b** 进入 Tmux 模式，再按第二键，例如：

- **[**：进入 Scroll  
- **Ctrl+b**（第二次）：向 shell 写入前缀（配置中为 `Write 2`）  
- **"** / **%** / **-** / **_**：分屏或新 Tab 等（与 `config.kdl` 中 `tmux` 块一致）  
- **h j k l** 或方向键：移动焦点并回到 Normal  
- **d**：detach  
- **x**：关闭焦点 pane 并回到 Normal  
- 更多键位见配置中 `tmux { ... }`  

## 本配置中的其它选项（摘录）

与键位无关、但影响行为的设置可在 `config.kdl` 中查看，例如：

- **theme**：`gruvbox-dark-hard`  
- **scroll_buffer_size**：`100000`  
- **scrollback_editor**：`nvim`  
- **show_release_notes** / **show_startup_tips**：`false`  
- **plugins**：内置插件别名（tab-bar、session-manager、strider 等）  

## 命令行常用用法

```bash
zellij                 # 启动新会话
zellij attach <名称>   # 附加到已有会话
zellij ls              # 列出会话
```

配置文件通常位于 `$XDG_CONFIG_HOME/zellij/config.kdl`（macOS 上多为 `~/.config/zellij/config.kdl`）。若使用本 dotfiles，请按你的安装方式将该目录或文件链到上述路径。

---

文档与 [`config.kdl`](config.kdl) 同步维护；键位或 `unbind` 变更时请一并更新本文。
