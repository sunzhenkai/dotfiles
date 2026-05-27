return {
  -- gopls v0.22+ 需要 Go 1.26 编译；GOTOOLCHAIN=local 时无法自动升级 toolchain
  {
    "neovim/nvim-lspconfig",
    opts = {
      servers = {
        gopls = {
          mason = false,
        },
      },
    },
  },
  {
    "mason-org/mason-lspconfig.nvim",
    opts = {
      ensure_installed = { "gopls@v0.20.0" },
    },
  },
}
