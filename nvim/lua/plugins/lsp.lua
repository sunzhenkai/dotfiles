return {
	{
		"neovim/nvim-lspconfig",
		event = "LazyFile",
		dependencies = {
			"mason.nvim",
			{ "williamboman/mason-lspconfig.nvim", config = function() end },
			-- "hrsh7th/nvim-cmp",
			-- "hrsh7th/cmp-nvim-lsp",
			-- c/c++
			"p00f/clangd_extensions.nvim",
		},
		opts = function()
			---@class PluginLspOpts
			return {
				-- options for vim.diagnostic.config()
				---@type vim.diagnostic.Opts
				diagnostics = {
					underline = true,
					update_in_insert = false,
					virtual_text = {
						spacing = 2,
						source = "if_many",
						prefix = "●",
						-- this will set set the prefix to a function that returns the diagnostics icon based on the severity
						-- this only works on a recent 0.10.0 build. Will be set to "●" when not supported
						-- prefix = "icons",
					},
					severity_sort = true,
					signs = {
						text = {
							[vim.diagnostic.severity.ERROR] = LazyVim.config.icons.diagnostics.Error,
							[vim.diagnostic.severity.WARN] = LazyVim.config.icons.diagnostics.Warn,
							[vim.diagnostic.severity.HINT] = LazyVim.config.icons.diagnostics.Hint,
							[vim.diagnostic.severity.INFO] = LazyVim.config.icons.diagnostics.Info,
						},
					},
				},
				-- Enable this to enable the builtin LSP inlay hints on Neovim >= 0.10.0
				-- Be aware that you also will need to properly configure your LSP server to
				-- provide the inlay hints.
				inlay_hints = {
					enabled = false,
					exclude = { "vue" }, -- filetypes for which you don't want to enable inlay hints
				},
				-- Enable this to enable the builtin LSP code lenses on Neovim >= 0.10.0
				-- Be aware that you also will need to properly configure your LSP server to
				-- provide the code lenses.
				codelens = {
					enabled = false,
				},
				-- add any global capabilities here
				capabilities = {
					workspace = {
						fileOperations = {
							didRename = true,
							willRename = true,
						},
					},
				},
				-- options for vim.lsp.buf.format
				-- `bufnr` and `filter` is handled by the LazyVim formatter,
				-- but can be also overridden when specified
				format = {
					formatting_options = nil,
					timeout_ms = nil,
				},
				-- LSP Server Settings
				---@type lspconfig.options
				servers = {
					-- c/c++
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
							return require("lspconfig.util").root_pattern(
								"Makefile",
								"configure.ac",
								"configure.in",
								"config.h.in",
								"meson.build",
								"meson_options.txt",
								"build.ninja"
							)(fname) or require("lspconfig.util").root_pattern(
								"compile_commands.json",
								"compile_flags.txt"
							)(fname) or require("lspconfig.util").find_git_ancestor(fname)
						end,
						capabilities = {
							offsetEncoding = { "utf-16" },
						},
						--	"--header-insertion=iwyu",
						cmd = {
							"clangd",
							"--background-index",
							"--clang-tidy",
							"--header-insertion=never",
							"--completion-style=detailed",
							"--fallback-style=google",
							"--log=error",
						},
						init_options = {
							usePlaceholders = true,
							completeUnimported = true,
							clangdFileStatus = true,
						},
					},
					-- golang
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
					-- json
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
					-- lua
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
					-- markdown
					marksman = {},
					-- python
					-- pyright = {
					-- 	settings = {
					-- 		python = {
					-- 			venvPath = vim.fn.getcwd() .. "/..",
					-- 			venv = ".venv,venv",
					-- 		},
					-- 	},
					-- },
					pylsp = {
						settings = {
							pylsp = {
								plugins = {
									pylint = { enabled = true },
									pycodestyle = { maxLineLength = 100 },
								},
							},
						},
					},
					-- typescript
					tsserver = {
						enabled = false,
					},
					ts_ls = {
						enabled = false,
					},
					vtsls = {
						-- explicitly add default filetypes, so that we can extend
						-- them in related extras
						filetypes = {
							"javascript",
							"javascriptreact",
							"javascript.jsx",
							"typescript",
							"typescriptreact",
							"typescript.tsx",
						},
						settings = {
							complete_function_calls = true,
							vtsls = {
								enableMoveToFileCodeAction = true,
								autoUseWorkspaceTsdk = true,
								experimental = {
									maxInlayHintLength = 30,
									completion = {
										enableServerSideFuzzyMatch = true,
									},
								},
							},
							typescript = {
								updateImportsOnFileMove = { enabled = "always" },
								suggest = {
									completeFunctionCalls = true,
								},
								inlayHints = {
									enumMemberValues = { enabled = true },
									functionLikeReturnTypes = { enabled = true },
									parameterNames = { enabled = "literals" },
									parameterTypes = { enabled = true },
									propertyDeclarationTypes = { enabled = true },
									variableTypes = { enabled = false },
								},
							},
						},
						keys = {
							{
								"gD",
								function()
									local params = vim.lsp.util.make_position_params()
									LazyVim.lsp.execute({
										command = "typescript.goToSourceDefinition",
										arguments = { params.textDocument.uri, params.position },
										open = true,
									})
								end,
								desc = "Goto Source Definition",
							},
							{
								"gR",
								function()
									LazyVim.lsp.execute({
										command = "typescript.findAllFileReferences",
										arguments = { vim.uri_from_bufnr(0) },
										open = true,
									})
								end,
								desc = "File References",
							},
							{
								"<leader>co",
								LazyVim.lsp.action["source.organizeImports"],
								desc = "Organize Imports",
							},
							{
								"<leader>cM",
								LazyVim.lsp.action["source.addMissingImports.ts"],
								desc = "Add missing imports",
							},
							{
								"<leader>cu",
								LazyVim.lsp.action["source.removeUnused.ts"],
								desc = "Remove unused imports",
							},
							{
								"<leader>cD",
								LazyVim.lsp.action["source.fixAll.ts"],
								desc = "Fix all diagnostics",
							},
							{
								"<leader>cV",
								function()
									LazyVim.lsp.execute({ command = "typescript.selectTypeScriptVersion" })
								end,
								desc = "Select TS workspace version",
							},
						},
					},
					-- yaml
					yamlls = {
						-- Have to add this for yamlls to understand that we support line folding
						capabilities = {
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
				},
				-- you can do any additional lsp server setup here
				-- return true if you don't want this server to be setup with lspconfig
				---@type table<string, fun(server:string, opts:_.lspconfig.options):boolean?>
				setup = {
					-- example to setup with typescript.nvim
					-- tsserver = function(_, opts)
					--   require("typescript").setup({ server = opts })
					--   return true
					-- end,
					-- Specify * to use this function as a fallback for any server
					-- ["*"] = function(server, opts) end,

					-- c/c++/cmake
					clangd = function(_, opts)
						local clangd_ext_opts = LazyVim.opts("clangd_extensions.nvim")
						require("clangd_extensions").setup(
							vim.tbl_deep_extend("force", clangd_ext_opts or {}, { server = opts })
						)
						return false
					end,
					-- golang
					gopls = function(_, opts)
						local has_cmp_nvim_lsp, cmp_nvim_lsp = pcall(require, "cmp_nvim_lsp")
						if has_cmp_nvim_lsp then
							local capabilities = cmp_nvim_lsp.default_capabilities()
							opts.capabilities = vim.tbl_deep_extend("force", opts.capabilities or {}, capabilities)
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
					-- typescript
					tsserver = function()
						-- disable tsserver
						return true
					end,
					ts_ls = function()
						-- disable tsserver
						return true
					end,
					vtsls = function(_, opts)
						LazyVim.lsp.on_attach(function(client, buffer)
							client.commands["_typescript.moveToFileRefactoring"] = function(command, ctx)
								---@type string, string, lsp.Range
								local action, uri, range = unpack(command.arguments)

								local function move(newf)
									client.request("workspace/executeCommand", {
										command = command.command,
										arguments = { action, uri, range, newf },
									})
								end

								local fname = vim.uri_to_fname(uri)
								client.request("workspace/executeCommand", {
									command = "typescript.tsserverRequest",
									arguments = {
										"getMoveToRefactoringFileSuggestions",
										{
											file = fname,
											startLine = range.start.line + 1,
											startOffset = range.start.character + 1,
											endLine = range["end"].line + 1,
											endOffset = range["end"].character + 1,
										},
									},
								}, function(_, result)
									---@type string[]
									local files = result.body.files
									table.insert(files, 1, "Enter new path...")
									vim.ui.select(files, {
										prompt = "Select move destination:",
										format_item = function(f)
											return vim.fn.fnamemodify(f, ":~:.")
										end,
									}, function(f)
										if f and f:find("^Enter new path") then
											vim.ui.input({
												prompt = "Enter move destination:",
												default = vim.fn.fnamemodify(fname, ":h") .. "/",
												completion = "file",
											}, function(newf)
												return newf and move(newf)
											end)
										elseif f then
											move(f)
										end
									end)
								end)
							end
						end, "vtsls")
						-- copy typescript settings to javascript
						opts.settings.javascript =
							vim.tbl_deep_extend("force", {}, opts.settings.typescript, opts.settings.javascript or {})
					end,
					-- yaml
					yamlls = function()
						-- Neovim < 0.10 does not have dynamic registration for formatting
						if vim.fn.has("nvim-0.10") == 0 then
							LazyVim.lsp.on_attach(function(client, _)
								client.server_capabilities.documentFormattingProvider = true
							end, "yamlls")
						end
					end,
					-- cmp-nvim-lsp config
					["*"] = function(_, opts)
						local has_cmp_nvim_lsp, cmp_nvim_lsp = pcall(require, "cmp_nvim_lsp")
						local has_cmp, cmp = pcall(require, "cmp")
						if has_cmp and has_cmp_nvim_lsp then
							local cmp_cap = require("cmp_nvim_lsp").default_capabilities()
							opts.capabilities = vim.tbl_deep_extend("force", opts.capabilities or {}, cmp_cap)
						end
					end,
				},
			}
		end,
		---@param opts PluginLspOpts
		config = function(_, opts)
			-- setup autoformat
			LazyVim.format.register(LazyVim.lsp.formatter())

			-- setup keymaps
			LazyVim.lsp.on_attach(function(client, buffer)
				require("lazyvim.plugins.lsp.keymaps").on_attach(client, buffer)
			end)

			LazyVim.lsp.setup()
			LazyVim.lsp.on_dynamic_capability(require("lazyvim.plugins.lsp.keymaps").on_attach)

			-- diagnostics signs
			if vim.fn.has("nvim-0.10.0") == 0 then
				if type(opts.diagnostics.signs) ~= "boolean" then
					for severity, icon in pairs(opts.diagnostics.signs.text) do
						local name = vim.diagnostic.severity[severity]:lower():gsub("^%l", string.upper)
						name = "DiagnosticSign" .. name
						vim.fn.sign_define(name, { text = icon, texthl = name, numhl = "" })
					end
				end
			end

			if vim.fn.has("nvim-0.10") == 1 then
				-- inlay hints
				if opts.inlay_hints.enabled then
					LazyVim.lsp.on_supports_method("textDocument/inlayHint", function(client, buffer)
						if
							vim.api.nvim_buf_is_valid(buffer)
							and vim.bo[buffer].buftype == ""
							and not vim.tbl_contains(opts.inlay_hints.exclude, vim.bo[buffer].filetype)
						then
							vim.lsp.inlay_hint.enable(true, { bufnr = buffer })
						end
					end)
				end

				-- code lens
				if opts.codelens.enabled and vim.lsp.codelens then
					LazyVim.lsp.on_supports_method("textDocument/codeLens", function(client, buffer)
						vim.lsp.codelens.refresh()
						vim.api.nvim_create_autocmd({ "BufEnter", "CursorHold", "InsertLeave" }, {
							buffer = buffer,
							callback = vim.lsp.codelens.refresh,
						})
					end)
				end
			end

			if type(opts.diagnostics.virtual_text) == "table" and opts.diagnostics.virtual_text.prefix == "icons" then
				opts.diagnostics.virtual_text.prefix = vim.fn.has("nvim-0.10.0") == 0 and "●"
					or function(diagnostic)
						local icons = LazyVim.config.icons.diagnostics
						for d, icon in pairs(icons) do
							if diagnostic.severity == vim.diagnostic.severity[d:upper()] then
								return icon
							end
						end
					end
			end

			vim.diagnostic.config(vim.deepcopy(opts.diagnostics))

			local servers = opts.servers
			local has_cmp, cmp_nvim_lsp = pcall(require, "cmp_nvim_lsp")
			local has_blink, blink = pcall(require, "blink.cmp")
			local capabilities = vim.tbl_deep_extend(
				"force",
				{},
				vim.lsp.protocol.make_client_capabilities(),
				has_cmp and cmp_nvim_lsp.default_capabilities() or {},
				has_blink and blink.get_lsp_capabilities() or {},
				opts.capabilities or {}
			)

			local function setup(server)
				local server_opts = vim.tbl_deep_extend("force", {
					capabilities = vim.deepcopy(capabilities),
				}, servers[server] or {})
				if server_opts.enabled == false then
					return
				end

				if opts.setup[server] then
					if opts.setup[server](server, server_opts) then
						return
					end
				elseif opts.setup["*"] then
					if opts.setup["*"](server, server_opts) then
						return
					end
				end
				require("lspconfig")[server].setup(server_opts)
			end

			-- get all the servers that are available through mason-lspconfig
			local have_mason, mlsp = pcall(require, "mason-lspconfig")
			local all_mslp_servers = {}
			if have_mason then
				all_mslp_servers = vim.tbl_keys(require("mason-lspconfig.mappings.server").lspconfig_to_package)
			end

			local ensure_installed = {} ---@type string[]
			for server, server_opts in pairs(servers) do
				if server_opts then
					server_opts = server_opts == true and {} or server_opts
					if server_opts.enabled ~= false then
						-- run manual setup if mason=false or if this is a server that cannot be installed with mason-lspconfig
						if server_opts.mason == false or not vim.tbl_contains(all_mslp_servers, server) then
							setup(server)
						else
							ensure_installed[#ensure_installed + 1] = server
						end
					end
				end
			end

			if have_mason then
				mlsp.setup({
					ensure_installed = vim.tbl_deep_extend(
						"force",
						ensure_installed,
						LazyVim.opts("mason-lspconfig.nvim").ensure_installed or {}
					),
					handlers = { setup },
				})
			end

			if LazyVim.lsp.is_enabled("denols") and LazyVim.lsp.is_enabled("vtsls") then
				local is_deno = require("lspconfig.util").root_pattern("deno.json", "deno.jsonc")
				LazyVim.lsp.disable("vtsls", is_deno)
				LazyVim.lsp.disable("denols", function(root_dir, config)
					if not is_deno(root_dir) then
						config.settings.deno.enable = false
					end
					return false
				end)
			end
		end,
	},
}
