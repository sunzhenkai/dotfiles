return {
  "akinsho/toggleterm.nvim",
  cmd = "ToggleTerm",
  build = ":ToggleTerm",
  version = "*",
  opts = { --[[ things you want to change go here]]
    direction = "float",
  },
  keys = {
    { "<C-/>", "<cmd>ToggleTerm<cr>", desc = "Open ToggleTerm" },
    { "<C-_>", "<cmd>ToggleTerm<cr>", desc = "Open ToggleTerm" },
    {
      "<Leader>tt",
      "<cmd>ToggleTerm<cr>",
      desc = "toggle terminal",
    },
  },
  --  vim.keymap.set(
  -- "n",
  -- "<leader>tt",
  -- ':lua require("toggleterm").toggle()<cr>',
  -- { desc = "toggle terminal", silent = true, noremap = true }
  --)
}
