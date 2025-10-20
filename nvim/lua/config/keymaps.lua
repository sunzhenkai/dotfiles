-- Keymaps are automatically loaded on the VeryLazy event
-- Default keymaps that are always set: https://github.com/LazyVim/LazyVim/blob/main/lua/lazyvim/config/keymaps.lua
-- Add any additional keymaps here
local keymap = vim.keymap
-- keymap.set("i", "ii", "<ESC>")

-- Diagnostics
keymap.set("n", "<C-n>", function()
	vim.diagnostic.jump({ count = 1, float = true, severity = { min = vim.diagnostic.severity.WARN } })
end)
keymap.set("n", "<C-m>", function()
	vim.diagnostic.jump({ count = 1, float = true, severity = vim.diagnostic.severity.ERROR })
end)

-- functions
-- information
local function get_datetime()
	return os.date("%Y-%m-%d %H:%M:%S") -- 如 "2023-10-05 14:30:00"
end
local function get_filename()
	return vim.fn.expand("%:t")
end
-- insert
local function insert_into_cursor(txt)
	-- 获取当前光标位置（行号从 1 开始，列号从 0 开始）
	local row = vim.fn.line(".") - 1 -- 转换为 0-based 行号
	local col = vim.fn.col(".") - 1 -- 转换为 0-based 列号
	vim.api.nvim_buf_set_text(0, row, col, row, col, { txt })
end

local function insert_multiple_lines(lines)
	local row = vim.fn.line(".") - 1 -- 当前行号（0-based）
	local line_count = vim.api.nvim_buf_line_count(0)
	-- 在下一行开始插入多行（利用 nvim_buf_set_lines）
	vim.api.nvim_buf_set_lines(0, row + 1, row + 1, true, lines)
	-- 调整光标到新插入的第一行的行首（可选）
	vim.api.nvim_win_set_cursor(0, { row + 2, 0 })
end

-- custome insert keymaps
-- insert file name
keymap.set("n", "<Leader>zif", function()
	insert_into_cursor(get_filename())
end, { desc = "Insert filename", silent = true, noremap = true })
-- insert datetime
keymap.set("n", "<Leader>zit", function()
	insert_into_cursor(get_datetime())
end, { desc = "Insert datetime", silent = true, noremap = true })

-- custome template keymaps
-- c++ file doxygen style comment
keymap.set("n", "<Leader>td", function()
	local lines_to_insert = {
		"/**",
		" * @file " .. get_filename(),
		" * @brief ",
		" * @author zhenkai.sun",
		" * @date " .. get_datetime(),
		-- " *",
		-- " * @details",
		-- " * ${2:details}",
		-- " * @example",
		-- " * ${3:example}",
		" */",
	}
	insert_multiple_lines(lines_to_insert)
end, { desc = "Insert doxygen style file comment", silent = true, noremap = true })

-- insert c++ function comment in doxygen style
keymap.set("n", "<Leader>tf", function()
	local lines_to_insert = {
		"/**",
		" * @brief ",
		-- " *",
		-- " * @details",
		-- " *",
		-- " * @example",
		" */",
	}
	insert_multiple_lines(lines_to_insert)
end, { desc = "Insert doxygen style function comment", silent = true, noremap = true })

-- 可视模式下 <leader>y 复制到系统剪贴板
keymap.set("v", "<leader>y", '"+y', {
	noremap = true, -- 非递归映射
	silent = true, -- 静默执行
	desc = "Copy to system clipboard", -- 可选的描述
})
-- 可视模式下 <leader>p 粘贴系统剪贴板内容
keymap.set("v", "<leader>p", '"+p', {
	noremap = true, -- 非递归映射
	silent = true, -- 静默执行
	desc = "Paste from system clipboard", -- 可选的描述
})

-- window size
vim.keymap.set("n", "<C-k>", "<cmd>resize +4<cr>", { desc = "Increase Window Height" })
vim.keymap.set("n", "<C-j>", "<cmd>resize -4<cr>", { desc = "Decrease Window Height" })
vim.keymap.set("n", "<C-h>", "<cmd>vertical resize +4<cr>", { desc = "Increase Window Width" })
vim.keymap.set("n", "<C-l>", "<cmd>vertical resize -4<cr>", { desc = "Decrease Window Width" })
