-- Autocmds are automatically loaded on the VeryLazy event
-- Default autocmds that are always set: https://github.com/LazyVim/LazyVim/blob/main/lua/lazyvim/config/autocmds.lua
-- Add any additional autocmds here
-- custom commands are preferred to start with 'I'

-- 在全局文本搜索是使用 Ctrl+R 粘贴寄存器内容
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
