-- 本机有源码检出就用它（改插件即时生效），没有就从 GitHub 拉
local local_dir = vim.fn.expand("~/code/repos/gh/wii/ave")

return {
  {
    "sunzhenkai/ave.nvim",
    dir = vim.fn.isdirectory(local_dir) == 1 and local_dir or nil,
    -- 启动即加载：<leader>a* 键位要一打开就能用
    event = "VeryLazy",
    config = function()
      -- 两个 agent 免确认启动：claude 跳过权限提示，codex 连沙箱一起关（只在自己信任的仓库里用）
      require("ave").setup({
        agents = {
          claude = { cmd = { "claude", "--permission-mode", "bypassPermissions" } },
          codex = { cmd = { "codex", "--dangerously-bypass-approvals-and-sandbox" } },
        },
      })
    end,
  },
}
