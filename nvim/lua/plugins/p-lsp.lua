local dft_capabilities = vim.lsp.protocol.make_client_capabilities()
dft_capabilities.general = dft_capabilities.general or {}
dft_capabilities.general.positionEncodings = { "utf-16" }

return {
	{
		"hrsh7th/cmp-nvim-lsp",
		enabled = true,
		dependencies = {
			"hrsh7th/nvim-cmp",
			"hrsh7th/cmp-buffer",
			"hrsh7th/cmp-path",
		},
	},
	-- neovim/nvim-lspconfig
	{
		"neovim/nvim-lspconfig",
		event = "LazyFile",
		dependencies = {
			"mason-org/mason.nvim",
			"mason-org/mason-lspconfig.nvim",
			"hrsh7th/cmp-nvim-lsp",
			-- c/c++
			"p00f/clangd_extensions.nvim",
		},
		opts = {
			servers = {
				pyright = {
					capabilities = dft_capabilities,
					disableLanguageServices = false,
					disableOrganizeImports = false,
					typeCheckingMode = "strict",
					python = {
						analysis = {
							django = true,
						},
					},
				},
				ruff = {
					capabilities = dft_capabilities,
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
				clangd = {
					filetypes = { "c", "cpp", "objc", "objcpp", "cuda", "hpp" },
					keys = {
						{
							"<leader>ch",
							"<cmd>ClangdSwitchSourceHeader<cr>",
							desc = "Switch Source/Header (C/C++)",
						},
					},
					root_dir = function(fname)
						if type(fname) ~= "string" then
							fname = vim.api.nvim_buf_get_name(0)
						end

						return require("lspconfig.util").root_pattern(
							"Makefile",
							"configure.ac",
							"configure.in",
							"config.h.in",
							"meson.build",
							"meson_options.txt",
							"build.ninja",
							"compile_commands.json",
							"compile_flags.txt",
							".git"
						)(fname)
					end,
					capabilities = dft_capabilities,
					cmd = {
						"clangd",
						"--background-index",
						"--clang-tidy",
						"--header-insertion=iwyu",
						"--completion-style=detailed",
						"--function-arg-placeholders",
						"--fallback-style=google",
						"--log=error",
					},
					init_options = {
						usePlaceholders = true,
						completeUnimported = true,
						clangdFileStatus = true,
					},
				},
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
				jsonls = {
					-- lazy-load schemastore when needed
					on_new_config = function(new_config)
						new_config.settings.json.schemas = new_config.settings.json.schemas or {}
						vim.list_extend(new_config.settings.json.schemas, require("schemastore").json.schemas())
					end,
					settings = {
						json = {
							format = {
								enable = true,
							},
							validate = { enable = true },
						},
					},
				},
				lua_ls = {
					-- mason = false, -- set to false if you don't want this server to be installed with mason
					-- Use this to add any additional keymaps
					-- for specific lsp servers
					-- ---@type LazyKeysSpec[]
					-- keys = {},
					settings = {
						Lua = {
							workspace = {
								checkThirdParty = false,
							},
							codeLens = {
								enable = true,
							},
							completion = {
								callSnippet = "Replace",
							},
							doc = {
								privateName = { "^_" },
							},
							hint = {
								enable = true,
								setType = false,
								paramType = true,
								paramName = "Disable",
								semicolon = "Disable",
								arrayIndex = "Disable",
							},
						},
					},
				},
				marksman = {},
				ts_ls = {
					filetypes = { "typescript", "typescriptreact", "typescript.tsx" },
					cmd = { "typescript-language-server", "--stdio" },
					settings = {
						completions = { completeFunctionCalls = true },
					},
				},
				yamlls = {
					-- Have to add this for yamlls to understand that we support line folding
					capabilities = {
						general = {
							offsetEncoding = { "utf-16" },
						},
						textDocument = {
							foldingRange = {
								dynamicRegistration = false,
								lineFoldingOnly = true,
							},
						},
					},
					-- lazy-load schemastore when needed
					on_new_config = function(new_config)
						new_config.settings.yaml.schemas = vim.tbl_deep_extend(
							"force",
							new_config.settings.yaml.schemas or {},
							require("schemastore").yaml.schemas()
						)
					end,
					settings = {
						redhat = { telemetry = { enabled = false } },
						yaml = {
							keyOrdering = false,
							format = {
								enable = true,
							},
							validate = true,
							schemaStore = {
								-- Must disable built-in schemaStore support to use
								-- schemas from SchemaStore.nvim plugin
								enable = false,
								-- Avoid TypeError: Cannot read properties of undefined (reading 'length')
								url = "",
							},
						},
					},
				},
				tsserver = {},
			},
			setup = {
				tsserver = function(_, opts)
					require("lspconfig").tsserver.setup(vim.tbl_deep_extend("force", opts, {
						filetypes = { "typescript", "typescriptreact", "javascript", "javascriptreact" },
						on_attach = function(client, bufnr)
							-- Disable built-in formatting in tsserver
							client.server_capabilities.documentFormattingProvider = false
							client.server_capabilities.documentRangeFormattingProvider = false
						end,
					}))
					return true
				end,
				clangd = function(_, opts)
					local clangd_ext_opts = LazyVim.opts("clangd_extensions.nvim")
					require("clangd_extensions").setup(
						vim.tbl_deep_extend("force", clangd_ext_opts or {}, { server = opts })
					)
					return false
				end,
				gopls = function(_, opts)
					local has_cmp_nvim_lsp, cmp_nvim_lsp = pcall(require, "cmp_nvim_lsp")
					if has_cmp_nvim_lsp then
						opts.capabilities = vim.tbl_deep_extend("force", opts.capabilities or {}, dft_capabilities)
					end
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
				yamlls = function()
					-- Neovim < 0.10 does not have dynamic registration for formatting
					if vim.fn.has("nvim-0.10") == 0 then
						LazyVim.lsp.on_attach(function(client, _)
							client.server_capabilities.documentFormattingProvider = true
							client.server_capabilities.hoverProvider = false
						end, "yamlls")
					end
				end,
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
