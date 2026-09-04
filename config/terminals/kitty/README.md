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

Kitty 使用注册表声明的 `copy` 策略。先预览，再将配置安装为 HOME 下的真实目录：

```shell
dotf kitty -c --dry-run
dotf kitty -c --yes
```

`~/.config/kitty` 不会链接回仓库，因此 Kitty 写入的本机状态不会反向进入源码。修改本仓库中的 Kitty 配置后，需要重新运行 `dotf kitty -c` 才会同步到 HOME。

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
