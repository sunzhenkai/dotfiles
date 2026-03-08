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

- `gopls` - Go 语言服务器
- `goimports` - 导入管理
- `gofumpt` - 代码格式化
- `golangci-lint` - 代码检查
- `delve` - Go 调试器
- `gomodifytags` - 结构体标签修改
- `impl` - 接口实现生成
