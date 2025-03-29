return {
  "danymat/neogen",
  config = function()
    require("neogen").setup({ snippet_engine = "luasnip" })
  end,
  keys = {
    {
      "<Leader>znc",
      "<cmd>lua require('neogen').generate({ type = 'class' })<CR>",
      desc = "Generate Class Documentation",
    },
    {
      "<Leader>znd",
      "<cmd>lua require('neogen').generate({ type = 'file' })<CR>",
      desc = "Generate File Documentation",
    },
    {
      "<Leader>znf",
      "<cmd>lua require('neogen').generate({ type = 'func' })<CR>",
      desc = "Generate Function Documentation",
    },
  },
  -- Uncomment next line if you want to follow only stable versions
  -- version = "*"
}
