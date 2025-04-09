-- Autocmds are automatically loaded on the VeryLazy event
-- Default autocmds that are always set: https://github.com/LazyVim/LazyVim/blob/main/lua/lazyvim/config/autocmds.lua
-- Add any additional autocmds here
-- custom commands are preferred to start with 'I'

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
vim.api.nvim_create_user_command("NewClangFmtFile", "%!clang-format -style=Google -dump-config > .clang-format", {})
-- format current file using ClangFmt
vim.api.nvim_create_user_command("ClangFmt", "%!clang-format --style=file", {})
