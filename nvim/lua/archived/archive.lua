return {
	-- cmp: completion
	-- hrsh7th/nvim-cmp
	{
		"hrsh7th/nvim-cmp",
		enabled = false,
		dependencies = {
			"hrsh7th/cmp-nvim-lsp",
			"hrsh7th/cmp-buffer",
			"hrsh7th/cmp-path",
			"hrsh7th/cmp-cmdline",
			"hrsh7th/vim-vsnip",
			"hrsh7th/cmp-vsnip",
		},
		config = function()
			local cmp = require("cmp")
			cmp.setup({
				snippet = {
					expand = function(args)
						vim.fn["vsnip#anonymous"](args.body)
					end,
				},
				mapping = cmp.mapping.preset.insert({
					["<C-b>"] = cmp.mapping.scroll_docs(-4),
					["<C-f>"] = cmp.mapping.scroll_docs(4),
					["<C-Space>"] = cmp.mapping.complete(),
					["<C-e>"] = cmp.mapping.abort(),
					["<CR>"] = cmp.mapping.confirm({ select = true }),
				}),
				sources = cmp.config.sources({
					{ name = "nvim_lsp" },
					{ name = "vsnip" },
				}, {
					{ name = "buffer" },
				}),
			})
		end,
		opts = function(_, opts)
			local has_words_before = function()
				unpack = unpack or table.unpack
				local line, col = unpack(vim.api.nvim_win_get_cursor(0))
				return col ~= 0
					and vim.api.nvim_buf_get_lines(0, line - 1, line, true)[1]:sub(col, col):match("%s") == nil
			end

			local cmp = require("cmp")

			opts.mapping = vim.tbl_extend("force", opts.mapping or {}, {
				["<Tab>"] = cmp.mapping(function(fallback)
					if cmp.visible() then
						-- You could replace select_next_item() with confirm({ select = true }) to get VS Code autocompletion behavior
						cmp.select_next_item()
					elseif vim.snippet.active({ direction = 1 }) then
						vim.schedule(function()
							vim.snippet.jump(1)
						end)
					elseif has_words_before() then
						cmp.complete()
					else
						fallback()
					end
				end, { "i", "s" }),
				["<S-Tab>"] = cmp.mapping(function(fallback)
					if cmp.visible() then
						cmp.select_prev_item()
					elseif vim.snippet.active({ direction = -1 }) then
						vim.schedule(function()
							vim.snippet.jump(-1)
						end)
					else
						fallback()
					end
				end, { "i", "s" }),
			})
		end,
	},
	-- saghen/blink.compat
	{
		"saghen/blink.compat",
		enabled = false,
		optional = true, -- make optional so it's only enabled if any extras need it
		-- use the latest release, via version = '*', if you also use the latest release for blink.cmp
		version = "*",
		-- lazy.nvim will automatically load the plugin when it's required by blink.cmp
		lazy = true,
		-- make sure to set opts so that lazy.nvim calls blink.compat's setup
		opts = {},
	},
	-- saghen/blink.cmp
	{
		"saghen/blink.cmp",
		enable = false,
		version = not vim.g.lazyvim_blink_main and "*",
		build = vim.g.lazyvim_blink_main and "cargo build --release",
		opts_extend = {
			"sources.completion.enabled_providers",
			"sources.compat",
			"sources.default",
		},
		dependencies = {
			"rafamadriz/friendly-snippets",
			"saghen/blink.compat",
		},
		event = "InsertEnter",

		---@module 'blink.cmp'
		---@type blink.cmp.Config
		opts = {
			snippets = {
				expand = function(snippet, _)
					return LazyVim.cmp.expand(snippet)
				end,
			},
			appearance = {
				-- sets the fallback highlight groups to nvim-cmp's highlight groups
				-- useful for when your theme doesn't support blink.cmp
				-- will be removed in a future release, assuming themes add support
				use_nvim_cmp_as_default = false,
				-- set to 'mono' for 'Nerd Font Mono' or 'normal' for 'Nerd Font'
				-- adjusts spacing to ensure icons are aligned
				nerd_font_variant = "mono",
			},
			completion = {
				accept = {
					-- experimental auto-brackets support
					auto_brackets = {
						enabled = true,
					},
				},
				menu = {
					draw = {
						treesitter = { "lsp" },
					},
				},
				documentation = {
					auto_show = true,
					auto_show_delay_ms = 200,
				},
				ghost_text = {
					enabled = vim.g.ai_cmp,
				},
			},

			-- experimental signature help support
			-- signature = { enabled = true },

			sources = {
				-- adding any nvim-cmp sources here will enable them
				-- with blink.compat
				compat = {},
				default = { "lsp", "path", "snippets", "buffer" },
			},

			cmdline = {
				enabled = false,
			},

			keymap = {
				-- preset = "enter",
				["<C-y>"] = { "select_and_accept" },
			},
		},
		---@param opts blink.cmp.Config | { sources: { compat: string[] } }
		config = function(_, opts)
			-- setup compat sources
			local enabled = opts.sources.default
			for _, source in ipairs(opts.sources.compat or {}) do
				opts.sources.providers[source] = vim.tbl_deep_extend(
					"force",
					{ name = source, module = "blink.compat.source" },
					opts.sources.providers[source] or {}
				)
				if type(enabled) == "table" and not vim.tbl_contains(enabled, source) then
					table.insert(enabled, source)
				end
			end

			-- add ai_accept to <Tab> key
			if not opts.keymap["<Tab>"] then
				if opts.keymap.preset == "super-tab" then -- super-tab
					opts.keymap["<Tab>"] = {
						require("blink.cmp.keymap.presets")["super-tab"]["<Tab>"][1],
						LazyVim.cmp.map({ "snippet_forward", "ai_accept" }),
						"fallback",
					}
				else -- other presets
					opts.keymap["<Tab>"] = {
						LazyVim.cmp.map({ "snippet_forward", "ai_accept" }),
						"fallback",
					}
				end
			end

			-- Unset custom prop to pass blink.cmp validation
			opts.sources.compat = nil

			-- check if we need to override symbol kinds
			for _, provider in pairs(opts.sources.providers or {}) do
				---@cast provider blink.cmp.SourceProviderConfig|{kind?:string}
				if provider.kind then
					local CompletionItemKind = require("blink.cmp.types").CompletionItemKind
					local kind_idx = #CompletionItemKind + 1

					CompletionItemKind[kind_idx] = provider.kind
					---@diagnostic disable-next-line: no-unknown
					CompletionItemKind[provider.kind] = kind_idx

					---@type fun(ctx: blink.cmp.Context, items: blink.cmp.CompletionItem[]): blink.cmp.CompletionItem[]
					local transform_items = provider.transform_items
					---@param ctx blink.cmp.Context
					---@param items blink.cmp.CompletionItem[]
					provider.transform_items = function(ctx, items)
						items = transform_items and transform_items(ctx, items) or items
						for _, item in ipairs(items) do
							item.kind = kind_idx or item.kind
							item.kind_icon = LazyVim.config.icons.kinds[item.kind_name] or item.kind_icon or nil
						end
						return items
					end

					-- Unset custom prop to pass blink.cmp validation
					provider.kind = nil
				end
			end

			require("blink.cmp").setup(opts)
		end,
	},
	-- cpp
	-- Civitasv/cmake-tools.nvim
	{
		"Civitasv/cmake-tools.nvim",
		enabled = false,
		lazy = true,
		init = function()
			local loaded = false
			local function check()
				local cwd = vim.fn.getcwd()
				if vim.fn.filereadable(cwd .. "/CMakeLists.txt") == 1 then
					require("lazy").load({ plugins = { "cmake-tools.nvim" } })
					loaded = true
				end
			end
			check()
			vim.api.nvim_create_autocmd("DirChanged", {
				callback = function()
					if not loaded then
						check()
					end
				end,
			})
		end,
		opts = {},
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
	-- coding
	-- ray-x/navigator.lua
	{
		"ray-x/navigator.lua",
		enabled = false,
		dependencies = {
			{ "hrsh7th/nvim-cmp" },
			{ "nvim-treesitter/nvim-treesitter" },
			{ "ray-x/guihua.lua", run = "cd lua/fzy && make" },
			{
				"ray-x/go.nvim",
				event = { "CmdlineEnter" },
				ft = { "go", "gomod" },
				build = ':lua require("go.install").update_all_sync()',
			},
			{
				"ray-x/lsp_signature.nvim", -- Show function signature when you type
				event = "VeryLazy",
				config = function()
					require("lsp_signature").setup()
				end,
			},
		},
		config = function()
			require("go").setup()
			require("navigator").setup({
				lsp_signature_help = true, -- enable ray-x/lsp_signature
				lsp = { format_on_save = true },
			})

			vim.api.nvim_create_autocmd("FileType", {
				pattern = { "go" },
				callback = function()
					-- CTRL/control keymaps
					vim.api.nvim_buf_set_keymap(0, "n", "<C-i>", ":GoImport<CR>", {})
					-- conflict with vim shotcut
					-- vim.api.nvim_buf_set_keymap(0, "n", "<C-b>", ":GoBuild %:h<CR>", {})
					vim.api.nvim_buf_set_keymap(0, "n", "<C-t>", ":GoTestPkg<CR>", {})
					vim.api.nvim_buf_set_keymap(0, "n", "<C-c>", ":GoCoverage -p<CR>", {})

					-- Opens test files
					vim.api.nvim_buf_set_keymap(0, "n", "A", ":lua require('go.alternate').switch(true, '')<CR>", {}) -- Test
					vim.api.nvim_buf_set_keymap(
						0,
						"n",
						"V",
						":lua require('go.alternate').switch(true, 'vsplit')<CR>",
						{}
					) -- Test Vertical
					vim.api.nvim_buf_set_keymap(
						0,
						"n",
						"S",
						":lua require('go.alternate').switch(true, 'split')<CR>",
						{}
					) -- Test Split
				end,
				group = vim.api.nvim_create_augroup("go_autocommands", { clear = true }),
			})
		end,
	},
	-- lspconfig
	{
		opts = {
			servers = {
				neocmake = {
					init_options = {
						format = {
							enable = true,
							line_length = 100,
						},
						lint = { enable = true },
					},
				},
				cmake = {
					settings = {
						cmake = {
							lint = {
								lineLength = 100,
							},
							formatting = {
								lineLength = 100,
							},
						},
					},
				},
			},
		},
	},
	{
		"mfussenegger/nvim-dap",
		optional = true,
		dependencies = {
			{
				"williamboman/mason.nvim",
				opts = function(_, opts)
					opts.ensure_installed = opts.ensure_installed or {}
					table.insert(opts.ensure_installed, "js-debug-adapter")
				end,
			},
		},
		opts = function()
			local dap = require("dap")
			if not dap.adapters["pwa-node"] then
				require("dap").adapters["pwa-node"] = {
					type = "server",
					host = "localhost",
					port = "${port}",
					executable = {
						command = "node",
						-- 💀 Make sure to update this path to point to your installation
						args = {
							LazyVim.get_pkg_path("js-debug-adapter", "/js-debug/src/dapDebugServer.js"),
							"${port}",
						},
					},
				}
			end
			if not dap.adapters["node"] then
				dap.adapters["node"] = function(cb, config)
					if config.type == "node" then
						config.type = "pwa-node"
					end
					local nativeAdapter = dap.adapters["pwa-node"]
					if type(nativeAdapter) == "function" then
						nativeAdapter(cb, config)
					else
						cb(nativeAdapter)
					end
				end
			end

			local js_filetypes = { "typescript", "javascript", "typescriptreact", "javascriptreact" }

			local vscode = require("dap.ext.vscode")
			vscode.type_to_filetypes["node"] = js_filetypes
			vscode.type_to_filetypes["pwa-node"] = js_filetypes

			for _, language in ipairs(js_filetypes) do
				if not dap.configurations[language] then
					dap.configurations[language] = {
						{
							type = "pwa-node",
							request = "launch",
							name = "Launch file",
							program = "${file}",
							cwd = "${workspaceFolder}",
						},
						{
							type = "pwa-node",
							request = "attach",
							name = "Attach",
							processId = require("dap.utils").pick_process,
							cwd = "${workspaceFolder}",
						},
					}
				end
			end
		end,
	},
}
