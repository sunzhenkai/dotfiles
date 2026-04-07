## 1. 修复 `<leader>sE` 搜索快捷键

- [x] 1.1 修改 `nvim/lua/config/keymaps.lua`：将 `<leader>sE` 的 keymap rhs 从 `function() LazyVim.pick(...) end` 改为直接传递 `LazyVim.pick("live_grep", { file_ignore_patterns = grep_no_test_exclude })`
- [ ] 1.2 验证：在 nvim 中按 `<leader>sE` 能唤起 live_grep 搜索框且结果排除测试文件

## 2. 修复 Go 保存自动格式化

- [x] 2.1 修改 `nvim/lua/plugins/p-mason.lua`：在 mason.nvim 的 `ensure_installed` 列表中添加 `"gofumpt"` 和 `"goimports-reviser"`
- [ ] 2.2 验证：`:Mason` 中确认 gofumpt 和 goimports-reviser 已安装
- [ ] 2.3 验证：打开 Go 文件，保存后代码自动格式化且 import 自动排序

## 3. 移除 picker 冲突

- [x] 3.1 修改 `nvim/lua/config/lazy.lua`：移除 `{ import = "lazyvim.plugins.extras.editor.snacks_picker" }` 行
- [ ] 3.2 验证：nvim 启动无 "picker already set" 警告
- [ ] 3.3 验证：`<leader>/` 正常唤起 grep 搜索（非终端）

## 4. 验证 `<leader>/` 终端行为

- [ ] 4.1 确认 `<leader>/` 在修复 picker 冲突后唤起的是 grep 而非终端
- [ ] 4.2 如仍为终端行为，检查终端模拟器按键映射是否拦截 `<C-/>`
