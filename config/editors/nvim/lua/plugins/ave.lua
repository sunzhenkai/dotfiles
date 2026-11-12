return {
  {
    name = "ave",
    dir = vim.fn.expand("~/code/repos/gh/wii/ave"),
    -- 启动即加载：<leader>a* 键位要一打开就能用
    event = "VeryLazy",
    config = function()
      require("ave").setup()
    end,
  },
}
