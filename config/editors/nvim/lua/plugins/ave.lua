-- 本机有源码检出就用它（改插件即时生效），没有就从 GitHub 拉
local local_dir = vim.fn.expand("~/code/repos/gh/wii/ave")

return {
  {
    "sunzhenkai/ave.nvim",
    dir = vim.fn.isdirectory(local_dir) == 1 and local_dir or nil,
    -- 启动即加载：<leader>a* 键位要一打开就能用
    event = "VeryLazy",
    config = function()
      require("ave").setup()
    end,
  },
}
