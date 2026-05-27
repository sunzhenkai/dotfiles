这是从 「LazyVim + 大量手写 override」（raw/plugins/）迁移到 「LazyVim extras 为主 + 极少量自定义」（lua/plugins/）之后的变化。

总体架构变化

┌──────────┬───────────────────────────────────┬──────────────────────────────────────────────────┐
│ 维度 │ raw/plugins/（旧） │ lua/plugins/（现） │
├──────────┼───────────────────────────────────┼──────────────────────────────────────────────────┤
│ 文件数量 │ 15 个，按功能拆分 │ 2 个（core.lua + lang-go.lua） │
│ 配置策略 │ 每个插件手写 opts / keys / config │ 功能交给 lua/config/lazy.lua 里的 LazyVim extras │
│ 是否生效 │ 已归档，不会被 lazy.nvim 加载 │ 通过 { import = "plugins" } 实际生效 │
│ 维护成本 │ 高，需自己跟进各插件变更 │ 低，主要跟 LazyVim 升级 │
└──────────┴───────────────────────────────────┴──────────────────────────────────────────────────┘

当前入口在 lua/config/lazy.lua：先 import 一长串 LazyVim extras，再 import 你的 lua/plugins/：

/home/wii/.config/dotfiles/nvim/lua/config/lazy.lua lines 17-25

require("lazy").setup({
spec = {
{ "LazyVim/LazyVim", import = "lazyvim.plugins" },
{ import = "lazyvim.plugins.extras.coding.nvim-cmp" },
-- ... 20+ extras ...
{ import = "lazyvim.plugins.extras.ai.sidekick" },
{ import = "lazyvim.plugins.extras.coding.neogen" },
{ import = "plugins" },
},

────────────────────────────────────────

配置哲学

旧方案（raw）：在 LazyVim 之上做「全栈定制」——编辑器、LSP、Mason、UI、语言、AI 各自一份配置，细到 formatters、linters、gopls 性能参数、Neo-tree 根目录逻辑等。

新方案（lua/plugins）：相信 LazyVim extras 的默认组合，只在必须处打补丁。目前真正保留的自定义只有 Go 的 gopls 版本锁定：

/home/wii/.config/dotfiles/nvim/lua/plugins/lang-go.lua lines 1-19

return {
-- gopls v0.22+ 需要 Go 1.26 编译；GOTOOLCHAIN=local 时无法自动升级 toolchain
{
"neovim/nvim-lspconfig",
opts = {
servers = {
gopls = {
mason = false,
},
},
},
},
{
"mason-org/mason-lspconfig.nvim",
opts = {
ensure_installed = { "gopls@v0.20.0" },
},
},
}

core.lua 几乎只是占位：

/home/wii/.config/dotfiles/nvim/lua/plugins/core.lua lines 1-3

return {
{ "LazyVim/LazyVim" },
}

（LazyVim 本体已在 lazy.lua 里 import，这里属于冗余声明。）

────────────────────────────────────────

按模块对比：你会失去 / 得到什么

1. 编辑器体验（raw/p-editor.lua）

┌────────────────────────────────────────────────────────────┬────────────────────────────────────────────────┐
│ 旧配置 │ 迁移后 │
├────────────────────────────────────────────────────────────┼────────────────────────────────────────────────┤
│ Snacks picker/terminal 跟随 Neo-tree 当前目录 │ 用 LazyVim 默认 cwd 逻辑，失去「跟树目录走」 │
│ conform：C/C++ 禁用保存时格式化，各语言 formatter 精细配置 │ 走 LazyVim prettier extra + 各 lang extra 默认 │
│ nvim-lint：cpplint、golangci-lint、ruff、eslint_d 等定制 │ 走 LazyVim 默认 lint（+ eslint extra） │
│ vim-matchup 括号匹配优化 │ 不再安装（lazy-lock.json 无此插件） │
│ nvim-ufo 代码折叠 │ 不再安装 │
│ treesitter ensure_installed 扩展列表 │ 走 LazyVim / lang extras 默认 │
└────────────────────────────────────────────────────────────┴────────────────────────────────────────────────┘

1. LSP（raw/p-lsp.lua）

┌──────────────────────────────────────────────────────────────────────────┬────────────────────────────────────────────┐
│ 旧配置 │ 迁移后 │
├──────────────────────────────────────────────────────────────────────────┼────────────────────────────────────────────┤
│ clangd 大量 CLI 参数（--clang-tidy、--background-index-priority=low 等） │ 走 lazyvim.plugins.extras.lang.clangd 默认 │
│ gopls 性能调优（directoryFilters、memoryMode、symbolMatcher 等） │ 只剩版本 pin + mason = false │
│ 全局 diagnostics 优化（insert 模式不更新等） │ LazyVim 默认 │
└──────────────────────────────────────────────────────────────────────────┴────────────────────────────────────────────┘

1. Mason（raw/p-mason.lua）

┌─────────────────────────────────────────────────────────────────┬────────────────────────┐
│ 旧配置 │ 迁移后 │
├─────────────────────────────────────────────────────────────────┼────────────────────────┤
│ 显式 ensure_installed：prettier、shfmt、stylua、buf、gofumpt 等 │ 各 lang extra 自动管理 │
│ 安装成功后触发 FileType 的 monkey patch │ 丢失 │
└─────────────────────────────────────────────────────────────────┴────────────────────────┘

1. UI（raw/p-ui.lua）

┌────────────────────────────────────────┬──────────────────────────────────────────────────────────┐
│ 旧配置 │ 迁移后 │
├────────────────────────────────────────┼──────────────────────────────────────────────────────────┤
│ gruvbox 主题强制启用 │ lazy-lock.json 无 gruvbox；LazyVim 默认多半是 tokyonight │
│ bufferline 自定义快捷键 / slant 分隔符 │ LazyVim 默认 bufferline │
│ Neo-tree IP 跳转到父目录 │ 丢失 自定义 command │
└────────────────────────────────────────┴──────────────────────────────────────────────────────────┘

1. C++ 增强（raw/lang-cpp.lua）

┌────────────────────────────────────────────────────┬────────────────────────────────────────────────────┐
│ 旧配置 │ 迁移后 │
├────────────────────────────────────────────────────┼────────────────────────────────────────────────────┤
│ clangd_extensions 快捷键（AST、Type Hierarchy 等） │ clangd extra 有基础能力，自定义键位丢失 │
│ Telescope 调用/被调用 hierarchy │ telescope 未在 lock 中；已切到 snacks_picker extra │
│ aerial.nvim 符号大纲 <leader>co │ 不再安装 │
│ :NewClangdConfig 生成 .clangd 模板 │ 丢失 │
└────────────────────────────────────────────────────┴────────────────────────────────────────────────────┘

1. Python（raw/lang-python.lua）

┌──────────────────────────────────────────────┬─────────────────────────────────────────┐
│ 旧配置 │ 迁移后 │
├──────────────────────────────────────────────┼─────────────────────────────────────────┤
│ pyright typeCheckingMode = "strict" + django │ 走 lang.python extra 默认（通常更宽松） │
└──────────────────────────────────────────────┴─────────────────────────────────────────┘

1. 工具 / AI

┌────────────────────────────────────────────────────┬──────────────────────────────────────────────────────┐
│ 旧配置 │ 迁移后 │
├────────────────────────────────────────────────────┼──────────────────────────────────────────────────────┤
│ tool-ai.lua：sidekick <leader>al CLI toggle │ ai.sidekick extra 已启用（sidekick.nvim 在 lock 中） │
│ p-utils.lua：lazygit.nvim │ 不再作为插件安装（README 仍建议系统装 lazygit CLI） │
│ p-image.lua：image/diagram（本就 enabled = false） │ 无变化，仍不可用 │
└────────────────────────────────────────────────────┴──────────────────────────────────────────────────────┘

1. Go

┌────────────────────────────────────────────────────────────┬────────────────────────────────────────────────────────────────┐
│ 旧配置 │ 迁移后 │
├────────────────────────────────────────────────────────────┼────────────────────────────────────────────────────────────────┤
│ archive/lang-go.lua 里大量注释掉的 go.nvim、Mason 工具列表 │ 完全不用 go.nvim │
│ — │ lang.go extra + neotest-golang + DAP；仅保留 gopls@v0.20.0 pin │
└────────────────────────────────────────────────────────────┴────────────────────────────────────────────────────────────────┘

────────────────────────────────────────

插件生态变化（从 lock 文件可见）

当前实际安装的（节选）：LazyVim 全家桶、snacks、sidekick、neotest、各 lang LSP、conform、nvim-lint、mason 等。

raw 里有、当前没有的：

• telescope.nvim → 被 snacks_picker 替代
• aerial.nvim、vim-matchup、nvim-ufo
• gruvbox.nvim、lazygit.nvim
• 以及 archive 里已禁用的 avante.nvim、blink.cmp 等

────────────────────────────────────────

优缺点总结

迁移到 lua/plugins/ + LazyVim extras 的好处：
• 配置从 ~800+ 行拆散 override 收敛到 ~20 行
• 升级 LazyVim 时冲突更少
• 语言栈（Go/Python/Rust/TS/C++ 等）由官方 extras 统一维护
• 测试/DAP/AI 等能力开箱即用（neotest、sidekick 等）

代价 / 风险：
• 大量「按你习惯打磨过」的行为回到 LazyVim 默认
• 性能向调优（gopls、clangd、matchup 延迟、lint 触发时机）基本消失
• 若干 workflow 快捷键失效（Neo-tree 根目录 picker、aerial 大纲、:NewClangdConfig 等）
• 主题从 gruvbox 变回 LazyVim 默认

────────────────────────────────────────

一句话结论

raw/plugins/ 是 「LazyVim 当底座，自己接管每个插件细节」；lua/plugins/ 是 「把细节还给 LazyVim，只留 toolchain 兼容补丁」。
功能面上不是「换了一套插件」，而是 从深度定制回到 LazyVim 标准发行版；若某些 raw 里的行为对你很重要，需要按需把对应片段迁回 lua/plugins/（利用 LazyVim 的 opts/keys 合并机制，README 里也提到了这一点）。
