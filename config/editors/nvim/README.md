# Nvim Config

# Dependencies

```shell
brew install fzf ripgrep luarocks lazygit hunspell imagemagick fd tectonic ghostscript

npm install -g yarn
npm install -g @mermaid-js/mermaid-cli

# ubuntu
sudo apt install build-essential libhunspell-dev
```

## qwen-code client

- [qwen-code](https://github.com/QwenLM/qwen-code)
  Install from npm

```shell
npm install -g @qwen-code/qwen-code@latest
qwen --version
```

Install from homebrew

```shell
brew install qwen-code
```

Config

```shell
qwen
```

# 字体

Neovim 的图标可能无法正常显示，需要安装字体。
[字体下载站点](https://www.nerdfonts.com/font-downloads)
可以使用 JetBrainsMono Nerd Font 字体。

# 概念

## LSP

LSP(Language Server Protocol) 是一个协议，用于在代码编辑器和编程语言的语言服务器之间进行通信。语言服务器提供语言特定的功能，如：

- 语法高亮
- 自动完成
- 代码检查（Linting）
- 跳转到定义
- 引用查找
- 重命名
- 文档说明
  Neovim 通过内置支持 LSP，使你能够将其与多种编程语言的语言服务器集成。通常，你会使用插件（如 nvim-lspconfig）来轻松设置和配置所需的语言服务器。

使用 LSP 的基本步骤：

1. 安装相应的语言服务器。
2. 使用 nvim-lspconfig 插件配置语言服务器。
3. 在编辑器中享受自动完成功能、错误提示等。

## DAP

DAP(Debug Adapter Protocol) 是一个用于调试程序的协议，允许调试器和 IDE/编辑器之间的通信。使用 DAP，开发者可以在 Neovim 中实现以下调试功能：

- 启动和停止调试会话
- 设置断点
- 单步执行
- 查看变量和表达式
- 调用堆栈查看
  与 LSP 类似，Neovim 可以通过插件（例如 nvim-dap）来支持 DAP 并连接到不同的调试适配器。

使用 DAP 的基本步骤：

1. 安装所需的调试适配器（如 debugpy 用于 Python，vscode-node-debug2 用于 Node.js）。
2. 使用 nvim-dap 插件进行配置。
3. 利用按键映射进行调试操作（如设置断点、启动调试等）。

# 自定义

以下字段 Lazyvim 的默认设置会和多个配置文件的相同字段合并：

- cmd
- event
- ft
- keys
- opts
- dependencies

除此之外的其他字段，自己配置的会覆盖默认配置.

# 检查

```shell
:checkhealth # 检查所有插件
```

# References

- [zjp-cn nvim0.6-blogs](https://zjp-cn.github.io/neovim0.6-blogs/index.html)

# Troubleshooting

## Avante

- 如果设置环境变量 OPENAI_API_KEY 且不可用，会出现奇怪的错误, 比如即便配置了其他的 provider 还是会往 openai 发送请求.

## 启动报错

如果遇到打开 nvim 时很多奇怪的报错，可以尝试同步插件.

```shell
:Lazy sync
```

# Go 测试

LazyVim 使用 [neotest](https://github.com/nvim-neotest/neotest) + [neotest-golang](https://github.com/fredrikaverpil/neotest-golang) 来运行 Go 测试。

## 测试快捷键

| 快捷键 | 描述 |
|--------|------|
| `<leader>t` | 测试菜单前缀 |
| `<leader>tt` | 运行当前文件的所有测试 |
| `<leader>tr` | 运行离光标最近的测试 |
| `<leader>tT` | 运行项目所有测试文件 |
| `<leader>tl` | 运行上次执行的测试 |
| `<leader>ta` | 附加到测试进程 |
| `<leader>ts` | 切换测试摘要面板 |
| `<leader>to` | 显示光标处测试的输出 |
| `<leader>tO` | 切换测试输出面板 |
| `<leader>tS` | 停止正在运行的测试 |
| `<leader>tw` | 切换测试监视模式（文件保存时自动运行） |
| `<leader>td` | 调试最近的测试（需要 DAP） |

## 测试参数配置

可在 `~/.config/nvim/lua/plugins/` 下创建配置文件自定义 `go test` 参数：

```lua
return {
  {
    "nvim-neotest/neotest",
    opts = {
      adapters = {
        ["neotest-golang"] = {
          go_test_args = { "-v", "-race", "-count=1", "-timeout=60s" },
          dap_go_enabled = true, -- 启用调试支持
        },
      },
    },
  },
}
```

## 依赖工具

LazyVim Go extra 会自动安装以下工具（通过 Mason）：

- `gopls` - Go 语言服务器（已固定版本，见下方说明）
- `goimports` - 导入管理（已从 Mason 移除，见下方说明）
- `gofumpt` - 代码格式化
- `golangci-lint` - 代码检查
- `delve` - Go 调试器
- `gomodifytags` - 结构体标签修改
- `impl` - 接口实现生成

## Go 工具版本兼容性

### 背景

本机使用 **mise** 管理 Go 版本，当前全局为 `go 1.24.x`，且设置了 `GOTOOLCHAIN=local`（mise/asdf 的默认行为，防止 Go 自动下载更新的 toolchain）。

在这种环境下，升级全局 Go 版本有实际风险：`go mod tidy` / `go get` 等命令会在 `go.mod` 中写入 `toolchain goX.Y.Z`，导致只有 Go 1.24 的 CI 或协作机器编译失败。

### 坑一：goimports 版本与 Go 版本不兼容

**现象：** Mason 安装 goimports 时报错：

```
golang.org/x/tools@v0.45.0 requires go >= 1.25.0 (running go 1.24.x; GOTOOLCHAIN=local)
```

**原因：** LazyVim go extra 在 Mason 的 `ensure_installed` 里注入的是裸的 `"goimports"`，
Mason 会取 registry 最新版（当前 `x/tools v0.45.0`），而该版本需要 Go 1.25+ 来**编译安装**。

**规律：**

| x/tools 版本 | 要求 Go |
|---|---|
| v0.43.0+ | Go 1.25+ |
| **v0.42.0** | **Go 1.24+** ✅ |

**解法：** 从 Mason 移除 goimports，在 `conform.nvim` 的 `init` 里检测并用 `go install` 异步安装固定版本（见 `lua/plugins/lang-go.lua`）。

> 升级全局 Go 到 1.25+ 后，可删除该 workaround，恢复 Mason 管理。

### 坑二：LazyVim 默认 Mason config 不支持 @version 语法

**现象：** 在 Mason 的 `ensure_installed` 里写 `"goimports@v0.42.0"` 无效，仍然安装最新版。

**原因：** LazyVim 的 Mason config 实现直接调用 `mr.get_package(tool):install()`，没有用 `Package.Parse` 解析 `@version`，版本号被忽略。`mason-lspconfig` 的 `ensure_installed` 支持 `@version`，但 `mason.nvim` 本身的不支持。

### 坑三：gofumpt 走 asdf shim 找不到版本

**现象：** conform.nvim 报错：

```
Formatter 'gofumpt' error: No version is set for command gofumpt
Consider adding one of the following versions: golang 1.25.0 / golang 1.24.10
```

**原因：** `gofumpt` 之前是在 Go 1.24.10 或 1.25.0 激活时通过 `go install` 安装的，
asdf shim（`~/.asdf/shims/gofumpt`）只记录了那两个版本。
切换到 Go 1.24.9 后，asdf 找不到对应的二进制。

```bash
# shim 内容示例
# asdf-plugin: golang 1.25.0
# asdf-plugin: golang 1.24.10
exec asdf exec "gofumpt" "$@"
```

**解法：** 用当前激活的 Go 版本重新安装，并 reshim：

```bash
go install mvdan.cc/gofumpt@latest
asdf reshim golang
```
