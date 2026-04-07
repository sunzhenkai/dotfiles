## Why

Neovim 配置存在三个功能缺陷：`<leader>sE` 搜索快捷键完全无响应、Go 文件保存时不自动格式化和导入依赖、以及 `<leader>/` 终端行为与预期不符。这些问题直接影响日常编码效率。

## What Changes

- 修复 `<leader>sE` 快捷键：`LazyVim.pick()` 返回值被外层匿名函数包裹导致实际 grep 函数未被调用，且 `exclude` 参数不被 `LazyVim.pick` 支持
- 修复 Go 保存时自动格式化：mason.nvim 的 `ensure_installed` 列表被 p-mason.lua 整体覆盖，导致 `gofumpt` 和 `goimports-reviser` 未安装
- 排查 `<leader>/` 按键行为：LazyVim 默认映射为 grep，但用户实际观察到终端 toggle 行为，需确认是否存在 picker 冲突或按键映射问题
- 移除 telescope 和 snacks_picker 双重导入的冲突：当前两个 picker extra 同时启用，只有一个能生效，另一个被静默拒绝

## Capabilities

### New Capabilities

_(无新增能力)_

### Modified Capabilities

_(无现有 spec 需要修改)_

## Impact

- `nvim/lua/config/keymaps.lua` — 修改 `<leader>sE` 的 keymap 定义
- `nvim/lua/plugins/p-mason.lua` — mason.nvim ensure_installed 列表需补充 Go 格式化工具
- `nvim/lua/config/lazy.lua` — 可能需要移除 telescope 或 snacks_picker 之一以消除冲突
- `nvim/lua/plugins/p-editor.lua` — 可能需要调整 Go formatter 配置
