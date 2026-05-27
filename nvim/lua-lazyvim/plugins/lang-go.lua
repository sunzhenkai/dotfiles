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
  -- goimports: mason registry 默认 x/tools v0.45.0 需 Go 1.25+；固定 v0.42.0 兼容 Go 1.24
  {
    "mason-org/mason.nvim",
    opts = function(_, opts)
      opts.ensure_installed = opts.ensure_installed or {}
      local out, seen = {}, {}
      for _, tool in ipairs(opts.ensure_installed) do
        if tool == "goimports" or tool:match("^goimports@") then
          tool = "goimports@v0.42.0"
        end
        if not seen[tool] then
          seen[tool] = true
          out[#out + 1] = tool
        end
      end
      opts.ensure_installed = out
    end,
    config = function(_, opts)
      require("mason").setup(opts)
      local Package = require("mason-core.package")
      local mr = require("mason-registry")
      mr:on("package:install:success", function()
        vim.defer_fn(function()
          require("lazy.core.handler.event").trigger({
            event = "FileType",
            buf = vim.api.nvim_get_current_buf(),
          })
        end, 100)
      end)
      mr.refresh(function()
        for _, tool in ipairs(opts.ensure_installed) do
          local name, version = Package.Parse(tool)
          local ok, p = pcall(mr.get_package, name)
          if ok and not p:is_installed() and not p:is_installing() then
            p:install({ version = version })
          end
        end
      end)
    end,
  },
}
