# Nvim Config

# Dependencies

```shell
brew install fzf ripgrep luarocks lazygit hunspell

npm install yarn -g

# ubuntu
sudo apt install build-essential libhunspell-dev
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

# 检查
```shell
:checkhealth # 检查所有插件
```

# References

- [zjp-cn nvim0.6-blogs](https://zjp-cn.github.io/neovim0.6-blogs/index.html)

