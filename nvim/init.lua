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
