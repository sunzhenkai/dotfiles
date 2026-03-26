-- Autocmds are automatically loaded on the VeryLazy event
-- Default autocmds that are always set: https://github.com/LazyVim/LazyVim/blob/main/lua/lazyvim/config/autocmds.lua
-- Add any additional autocmds here
-- custom commands are preferred to start with 'I'

-- 大文件优化: 对大文件禁用耗性能的功能
local big_file_group = vim.api.nvim_create_augroup("BigFileOptimization", { clear = true })
vim.api.nvim_create_autocmd("BufReadPre", {
	group = big_file_group,
	callback = function(args)
		local ok, stats = pcall(vim.uv.fs_stat, vim.api.nvim_buf_get_name(args.buf))
		if ok and stats and stats.size > 1024 * 1024 then -- 1MB
			vim.b[args.buf].large_file = true
			vim.opt_local.foldmethod = "manual"
			vim.opt_local.spell = false
			vim.opt_local.swapfile = false
			vim.opt_local.undofile = false
			-- 延迟禁用 treesitter 高亮
			vim.schedule(function()
				if vim.api.nvim_buf_is_valid(args.buf) then
					pcall(vim.treesitter.stop, args.buf)
				end
			end)
		end
	end,
})

-- Using C-r to get content from register in Global Scope
vim.cmd([[
  autocmd! FileType fzf tnoremap <expr> <C-r> getreg()
]])

-- show ansi escapes
-- usage: nvim +TermShow
vim.api.nvim_create_user_command("TermShow", function(args)
	local buf = vim.api.nvim_get_current_buf()
	local b = vim.api.nvim_create_buf(false, true)
	local chan = vim.api.nvim_open_term(b, {})
	vim.api.nvim_chan_send(chan, table.concat(vim.api.nvim_buf_get_lines(buf, 0, -1, false), "\n"))
	vim.api.nvim_win_set_buf(0, b)
end, {})

-- close current tab, and move to next one
vim.api.nvim_create_user_command("Ibd", "bd | bn", {})
vim.api.nvim_create_user_command("Ibdp", "bd | bp", {})
-- %bd: close all bufer, e# : edit the lastone, bd#: close the no name buffer
vim.api.nvim_create_user_command("Ibdo", "%bd | e# | bd#", {})
vim.api.nvim_create_user_command("NewClangFmtFile", function()
	vim.fn.system("clang-format -style=Google -dump-config > .clang-format")
	vim.notify("Generated .clang-format", vim.log.levels.INFO)
end, {})
-- format current file using ClangFmt
vim.api.nvim_create_user_command("ClangFmt", "%!clang-format --style=file", {})
