-- return {
--   -- theme
--   -- add gruvbox
--   { "ellisonleao/gruvbox.nvim", priority = 1000, config = true },
--   -- configure lazyvim to load gruvbox
--   {
--     "lazyvim/lazyvim",
--     opts = {
--       colorscheme = "gruvbox",
--     },
--   },
-- }
return {
  "ellisonleao/gruvbox.nvim",
  priority = 1000,
  config = function()
    require("gruvbox").setup({})
    vim.o.background = "light"
    vim.cmd("colorscheme gruvbox")
  end,
  opts = {},
}
