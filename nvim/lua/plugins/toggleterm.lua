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
  },
}
