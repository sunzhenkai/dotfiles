return {
	{
		"linux-cultist/venv-selector.nvim",
		dependencies = {
			"neovim/nvim-lspconfig",
			"mfussenegger/nvim-dap",
			"mfussenegger/nvim-dap-python", --optional
			"nvim-telescope/telescope.nvim",
		},
		lazy = false,
		branch = "regexp", -- This is the regexp branch, use this for the new version
		keys = {
			{ ",v", "<cmd>VenvSelect<cr>" },
		},
		opts = {
			-- Your settings go here
			name = "venv",
			auto_refresh = true,
			search_venv_managers = true,
			search_workspace = true,
		},
	},
	{
		"williamboman/mason.nvim",
		opts = {
			-- https://github.com/williamboman/mason-lspconfig.nvim
			ensure_installed = {
				"black",
				"ruff",
				"python-lsp-server",
				"pyright",
			},
		},
	},
	{
		"stevearc/conform.nvim",
		opts = {
			formatters_by_ft = {
				python = { "black", "ruff" },
			},
			formatters = {
				black = {
					prepend_args = { "--line-length", "100" },
				},
			},
		},
	},
	{
		"nvim-treesitter/nvim-treesitter",
		opts = { ensure_installed = { "ninja", "rst", "python" } },
	},
	{
		"neovim/nvim-lspconfig",
		opts = {
			servers = {
				ruff = {
					cmd_env = { RUFF_TRACE = "messages" },
					init_options = {
						settings = {
							logLevel = "error",
						},
					},
					keys = {
						{
							"<leader>co",
							LazyVim.lsp.action["source.organizeImports"],
							desc = "Organize Imports",
						},
					},
				},
				ruff_lsp = {
					keys = {
						{
							"<leader>co",
							LazyVim.lsp.action["source.organizeImports"],
							desc = "Organize Imports",
						},
					},
				},
			},
			setup = {
				on_attach = function(client, bufnr)
					client.server_capabilities.hoverProvider = false
				end,
			},
		},
	},
	{
		"neovim/nvim-lspconfig",
		opts = function(_, opts)
			local servers = { "pyright", "basedpyright", "ruff", "ruff_lsp", ruff, lsp }
			for _, server in ipairs(servers) do
				opts.servers[server] = opts.servers[server] or {}
				opts.servers[server].enabled = server == lsp or server == ruff
			end
		end,
	},
	{
		"neovim/nvim-lspconfig",
		dependencies = {},
		opts = {
			servers = {
				-- pyright = {},
				pylsp = {
					mason = false,
					settings = {
						pylsp = {
							plugins = {
								rope_autoimport = {
									enabled = true,
								},
							},
						},
					},
				},
				-- ruff_lsp = {
				--   -- handlers = {
				--   --   ["textDocument/publishDiagnostics"] = function() end,
				--   -- },
				-- },
				jedi_language_server = {},
			},
			setup = {
				pylsp = function()
					LazyVim.lsp.on_attach(function(client, _)
						if client.name == "pylsp" then
							-- disable hover in favor of jedi-language-server
							client.server_capabilities.hoverProvider = false
						end
					end)
				end,
				-- ruff_lsp = function()
				--   require("lazyvim.util").lsp.on_attach(function(client, _)
				--     if client.name == "ruff_lsp" then
				--       -- Disable hover in favor of Pyright
				--       client.server_capabilities.hoverProvider = false
				--     end
				--   end)
				-- end,
				pyright = function()
					require("lazyvim.util").lsp.on_attach(function(client, _)
						if client.name == "pyright" then
							-- disable hover in favor of jedi-language-server
							client.server_capabilities.hoverProvider = false
						end
					end)
				end,
			},
		},
	},
}
