return {
  {
    name = "ave",
    dir = vim.fn.expand("~/code/repos/gh/wii/ave"),
    cmd = "Ave",
    config = function()
      require("ave").setup()
    end,
  },
}
