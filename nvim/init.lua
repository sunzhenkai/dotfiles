-- 在全局文本搜索是使用 Ctrl+R 粘贴寄存器内容
--* Method 1
--* local autogrp = vim.api.nvim_create_augroup("FZF", { clear = true })
--* vim.api.nvim_create_autocmd("FileType", {
--* 	pattern = "fzf",
--* 	group = autogrp,
--* 	callback = function()
--* 		vim.api.nvim_set_keymap("t", "<C-r>", "getreg()", { noremap = true, expr = true, silent = true })
--* 	end,
--* })
--* "getreg(nr2char(getchar()))",
--* Method 2
vim.cmd([[
  autocmd! FileType fzf tnoremap <expr> <C-r> getreg()
]])

-- bootstrap lazy.nvim, LazyVim and your plugins
require("config.lazy")

vim.opt.clipboard = "unnamedplus"

vim.g.clipboard = {
  name = "OSC 52",
  copy = {
    ["+"] = require("vim.ui.clipboard.osc52").copy("+"),
    ["*"] = require("vim.ui.clipboard.osc52").copy("*"),
  },
  paste = {
    ["+"] = require("vim.ui.clipboard.osc52").paste("+"),
    ["*"] = require("vim.ui.clipboard.osc52").paste("*"),
  },
}

-- show ansi escapes
-- usage: nvim +TermShow
vim.api.nvim_create_user_command("TermShow", function(args)
    local buf = vim.api.nvim_get_current_buf()
    local b = vim.api.nvim_create_buf(false, true)
    local chan = vim.api.nvim_open_term(b, {})
    vim.api.nvim_chan_send(chan, table.concat(vim.api.nvim_buf_get_lines(buf, 0, -1, false), "\n"))
    vim.api.nvim_win_set_buf(0, b)
end, {})
