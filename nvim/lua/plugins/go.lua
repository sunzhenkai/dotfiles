return {
  {
    "ray-x/go.nvim",
    enabled = true,
    dependencies = { -- optional packages
      "ray-x/guihua.lua",
      "neovim/nvim-lspconfig",
      "nvim-treesitter/nvim-treesitter",
    },
    config = function()
      require("go").setup()
    end,
    event = { "CmdlineEnter" },
    ft = { "go", "gomod" },
    build = ':lua require("go.install").update_all_sync()', -- if you need to install/update all binaries
  },
  {
    "olexsmir/gopher.nvim",
    ft = "go",
    enabled = false,
    -- branch = "develop"
    -- (optional) will update plugin's deps on every update
    build = function()
      vim.cmd.GoInstallBinaries()
    end,
    ---@type gopher.Config
    opts = {},
  },
  {
    "neovim/nvim-lspconfig",
    opts = {
      servers = {
        gopls = {
          settings = {
            gopls = {
              -- gofumpt = true,
              codelenses = {
                gc_details = false,
                generate = true,
                regenerate_cgo = true,
                run_govulncheck = true,
                test = true,
                tidy = true,
                upgrade_dependency = true,
                vendor = true,
              },
              hints = {
                assignVariableTypes = true,
                compositeLiteralFields = true,
                compositeLiteralTypes = true,
                constantValues = true,
                functionTypeParameters = true,
                parameterNames = true,
                rangeVariableTypes = true,
              },
              analyses = {
                nilness = true,
                unusedparams = true,
                unusedwrite = true,
                useany = true,
              },
              usePlaceholders = true,
              completeUnimported = true,
              staticcheck = true,
              directoryFilters = { "-.git", "-.vscode", "-.idea", "-.vscode-test", "-node_modules" },
              semanticTokens = true,
            },
          },
        },
      },
      setup = {
        gopls = function(_, opts)
          local capabilities = require("cmp_nvim_lsp").default_capabilities()
          opts.capabilities = vim.tbl_deep_extend("force", opts.capabilities or {}, capabilities)
          -- workaround for gopls not supporting semanticTokensProvider
          -- https://github.com/golang/go/issues/54531#issuecomment-1464982242
          LazyVim.lsp.on_attach(function(client, _)
            if not client.server_capabilities.semanticTokensProvider then
              local semantic = client.config.capabilities.textDocument.semanticTokens
              client.server_capabilities.semanticTokensProvider = {
                full = true,
                legend = {
                  tokenTypes = semantic.tokenTypes,
                  tokenModifiers = semantic.tokenModifiers,
                },
                range = true,
              }
            end
          end, "gopls")
          -- end workaround
        end,
      },
    },
  },
  {
    "leoluz/nvim-dap-go",
    ft = "go",
    enabled = false,
    dependencies = {
      "mfussenegger/nvim-dap",
      "rcarriga/nvim-dap-ui",
    },
    config = function()
      require("dap-go").setup()
    end,
  },
  {
    "williamboman/mason.nvim",
    opts = {
      ensure_installed = {
        -- lsp
        "gopls",
        -- debug
        "go-debug-adapter",
        -- "delve",
        -- formatter
        "goimports-reviser",
        "golines",
        -- lint
        "golangci-lint",
        "golangci-lint-langserver",
        -- test
        "gotests",
        "gotestsum",
        -- generate
        "gomodifytags",
        -- "impl",
      },
    },
  },
  {
    "nvim-neotest/neotest",
    enabled = false,
    dependencies = {
      "nvim-lua/plenary.nvim",
      "fredrikaverpil/neotest-golang",
      "nvim-neotest/nvim-nio",
    },
    config = function()
      require("neotest").setup({
        adapters = {
          require("neotest-golang")({
            args = { "-count=1", "-timeout=60s" },
          }),
        },
      })
    end,
  },
  { -- Autoformat
    "stevearc/conform.nvim",
    lazy = false,
    opts = {
      formatters_by_ft = {
        go = { "gofumpt", "goimports-reviser" },
      },
    },
  },
}
