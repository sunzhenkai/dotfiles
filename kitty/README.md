# kitty

本目录为 **Kitty** 终端配置，由 WezTerm 配置迁移并持续维护；原始 WezTerm 配置仍保留在仓库 `wezterm/` 供对照。

## 文档

| 文档 | 说明 |
|------|------|
| [USAGE.md](USAGE.md) | **使用说明**：安装、日常操作、改配置与文档索引 |
| [keybindings.md](keybindings.md) | 快捷键：迁移后的 `Ctrl+a` 风格前缀、子模式与 Kitty 默认键补充 |
| [configuration-zh.md](configuration-zh.md) | 配置项按功能整理的中文摘要（完整选项以官方为准） |
| [kitty.conf 官方手册](https://sw.kovidgoyal.net/kitty/conf/) | 上游完整说明 |

## 应用方式

将本仓库中的 `kitty/` 链到你本机配置文件目录，例如：

```shell
ln -s "$(pwd)/kitty" ~/.config/kitty
```

若你使用其它 dotfile 管理方式，保持 `~/.config/kitty/kitty.conf` 指向或包含本仓库内容即可。

本目录中的 **`macos-launch-services-cmdline`** 用于在 **macOS 上从 GUI 启动** 时附加 `--start-as=fullscreen`；说明见 [USAGE.md](USAGE.md) 第 2 节。

## 生成默认参考配置（可选）

```shell
kitty +runpy 'from kitty.config import *; print(commented_out_default_config())'
```

## 验证配置（建议）

```shell
kitty --version
kitty --debug-config
```

在已运行的 Kitty 中可使用 **`Ctrl+Shift+F5`** 重载配置。
