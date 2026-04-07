## Context

当前 nvim 配置基于 LazyVim，使用 conform.nvim 管理格式化，mason.nvim 管理工具安装，snacks.nvim 提供终端功能。同时导入了 telescope 和 snacks_picker 两个 picker extra，存在冲突。

## Goals / Non-Goals

**Goals:**
- `<leader>sE` 正常唤起 live_grep，排除测试文件
- Go 文件保存时自动执行 gofumpt 格式化和 goimports-reviser 导入排序
- 消除 telescope 与 snacks_picker 的双重导入冲突
- 终端 toggle 行为符合预期（单实例切换）

**Non-Goals:**
- 不更换 picker 方案（保留用户现有选择）
- 不调整 Go LSP (gopls) 配置
- 不修改终端样式或布局

## Decisions

### 1. `<leader>sE` 修复方式

将 `LazyVim.pick()` 返回的函数直接作为 keymap 的 rhs，不再包裹在匿名函数中：

```lua
-- Before (broken):
keymap.set("n", "<leader>sE", function()
    LazyVim.pick("live_grep", { exclude = grep_no_test_exclude })
end, ...)

-- After (fixed):
keymap.set("n", "<leader>sE", LazyVim.pick("live_grep", {
    file_ignore_patterns = grep_no_test_exclude,
}), ...)
```

使用 `file_ignore_patterns` 替代 `exclude`，因为 LazyVim.pick 会将 opts 透传给底层 picker，而 telescope/snacks 的 grep 均支持 `file_ignore_patterns`。

### 2. Go 格式化工具安装

在 `p-mason.lua` 的 mason.nvim `ensure_installed` 中补充 `gofumpt` 和 `goimports-reviser`，与现有列表合并而非覆盖。

### 3. Picker 冲突解决

移除 `lazy.lua` 中的 `snacks_picker` extra 导入，保留 `telescope`。原因：
- telescope 在 `lazy.lua` 中先于 snacks_picker 导入，实际生效的已经是 telescope
- snacks_picker 被静默拒绝但仍然加载，产生无意义的警告
- 保留一个 picker 避免歧义

### 4. `<leader>/` 终端行为

如果移除 snacks_picker 冲突后 `<leader>/` 仍表现为终端 toggle，需进一步检查用户终端模拟器的按键映射是否拦截了 `<C-/>`。

## Risks / Trade-offs

- **[移除 snacks_picker]** → 如果用户未来想用 snacks picker，需重新添加并移除 telescope。低风险，当前 snacks_picker 本就没有生效。
- **[file_ignore_patterns]** → 不同 picker 对此参数的实现可能有细微差异（如 glob 语法），需在 telescope 和 snacks 中分别验证。实际上只保留 telescope 后不存在此问题。
