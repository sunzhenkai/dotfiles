return {
	-- auto-formatter
	{
		"stevearc/conform.nvim",
		opts = {
			notify_on_error = true,
			opts = {
				formatters_by_ft = {
					lua = { "stylua" },
					sh = { "shfmt" },
					c = { "clang_format" },
					cpp = { "clang_format" },
					go = { "gofumpt", "goimports-reviser" },
					markdown = { "prettier", "markdownlint-cli2" },
					yaml = { "yamlfmt" },
					toml = { "taplo" },
					json = { "prettier" },
					css = { "prettier" },
					python = { "black", "ruff" },
					typescriptreact = { "eslint_d" },
					typescript = { "eslint_d" },
					javascript = { "eslint_d" },
					javascriptreact = { "eslint_d" },
					proto = { "buf" },
				},
				formatters = {
					shfmt = {
						prepend_args = { "-i", "2" },
					},
					clang_format = {
						prepend_args = { "--style=file", "--fallback-style=google", "--verbose" },
					},
					-- python
					black = {
						prepend_args = { "--line-length", "100" },
					},
				},
			},
		},
	},
	-- andymass/vim-matchup
	-- code block match up
	{
		"andymass/vim-matchup",
		event = "BufReadPost",
		config = function()
			vim.g.matchup_matchparen_enabled = 1
			vim.g.matchup_matchparen_hi_surround_always = 1
			vim.g.matchup_matchparen_deferred = 1
		end,
	},
	-- nvim-treesitter/nvim-treesitter
	{
		"nvim-treesitter/nvim-treesitter",
		opts = {
			highlight = { enable = true },
			-- bugs found in cc file
			indent = { enable = false },
			ensure_installed = {
				"bash",
				"diff",
				"html",
				"lua",
				"luadoc",
				"luap",
				"printf",
				"query",
				"regex",
				"toml",
				"vim",
				"vimdoc",
				"xml",
				"yaml",
				-- c/c++/cmake
				"cmake",
				"cpp",
				"c",
				"make",
				"go",
				"proto",
				"typescript",
				"tsx",
				"python",
			},
		},
	},
	-- mfussenegger/nvim-lint
	{
		"mfussenegger/nvim-lint",
		event = "LazyFile",
		opts = {
			-- Event to trigger linters
			events = { "BufWritePost", "BufReadPost", "InsertLeave" },
			linters_by_ft = {
				-- c/c++/cmake
				c = { "cpplint" },
				cpp = { "cpplint" },
				-- fish
				fish = { "fish" },
				-- go
				go = { "golangcilint" },
				proto = { "protolint" },
				-- python
				python = { "ruff" },
				typescriptreact = { "eslint_d" },
				typescript = { "eslint_d" },
				javascript = { "eslint_d" },
				javascriptreact = { "eslint_d" },
			},
			-- LazyVim extension to easily override linter options
			-- or add custom linters.
			---@type table<string,table>
			linters = {
				-- -- Example of using selene only when a selene.toml file is present
				-- selene = {
				--   -- `condition` is another LazyVim extension that allows you to
				--   -- dynamically enable/disable linters based on the context.
				--   condition = function(ctx)
				--     return vim.fs.find({ "selene.toml" }, { path = ctx.filename, upward = true })[1]
				--   end,
				-- },
				-- c/c++/cmake
				cpplint = {
					args = {
						"--filter=-legal/copyright,-build/include_subdir,-runtime/indentation_namespace",
						-- set line length, the default value is 80
						"--linelength=120",
					},
				},
				eslint_d = {
					cmd = "eslint_d",
					args = { "--stdin", "--stdin-filename", "%filepath" },
					stream = "stderr",
					ignore_exitcode = true,
					parser = require("lint.parser").from_errorformat("%f:%l:%c: %m", {
						source = "eslint_d",
						severity = vim.diagnostic.severity.WARN,
					}),
				},
			},
		},
	},
	-- numToStr/Comment.nvim
	{
		"numToStr/Comment.nvim",
		opts = {
			-- add any options here
		},
	},
	-- folke/trouble.nvim
	{
		"folke/trouble.nvim",
		-- opts will be merged with the parent spec
		opts = { use_diagnostic_signs = true },
	},
	-- danymat/neogen
	{
		"danymat/neogen",
		config = function()
			require("neogen").setup({ snippet_engine = "luasnip" })
		end,
		keys = {
			{
				"<Leader>znc",
				"<cmd>lua require('neogen').generate({ type = 'class' })<CR>",
				desc = "Generate Class Documentation",
			},
			{
				"<Leader>znd",
				"<cmd>lua require('neogen').generate({ type = 'file' })<CR>",
				desc = "Generate File Documentation",
			},
			{
				"<Leader>znf",
				"<cmd>lua require('neogen').generate({ type = 'func' })<CR>",
				desc = "Generate Function Documentation",
			},
		},
		-- Uncomment next line if you want to follow only stable versions
		-- version = "*"
	},
	-- echasnovski/mini.pairs
	{
		"echasnovski/mini.pairs",
		event = "VeryLazy",
		opts = {
			modes = { insert = true, command = true, terminal = false },
			-- skip autopair when next character is one of these
			skip_next = [=[[%w%%%'%[%"%.%`%$]]=],
			-- skip autopair when the cursor is inside these treesitter nodes
			skip_ts = { "string" },
			-- skip autopair when next character is closing pair
			-- and there are more closing pairs than opening pairs
			skip_unbalanced = true,
			-- better deal with markdown code blocks
			markdown = true,
		},
		config = function(_, opts)
			LazyVim.mini.pairs(opts)
		end,
	},
	-- folke/lazydev.nvim
	{
		"folke/lazydev.nvim",
		ft = "lua",
		cmd = "LazyDev",
		opts = {
			library = {
				{ path = "${3rd}/luv/library", words = { "vim%.uv" } },
				{ path = "LazyVim", words = { "LazyVim" } },
				{ path = "snacks.nvim", words = { "Snacks" } },
				{ path = "lazy.nvim", words = { "LazyVim" } },
			},
		},
	},
	-- code folder
	-- kevinhwang91/nvim-ufo
	{
		"kevinhwang91/nvim-ufo",
		dependencies = {
			"kevinhwang91/promise-async",
			"neovim/nvim-lspconfig",
		},
		setup = function()
			require("ufo").setup()
		end,
	},
	-- none-ls / null_ls
	{
		"nvimtools/none-ls.nvim",
		enabled = false,
		optional = true,
		dependencies = {
			"nvimtools/none-ls-extras.nvim",
		},
		opts = function(_, opts)
			local nls = require("null-ls")
			opts.sources = vim.list_extend(opts.sources or {}, {
				nls.builtins.code_actions.gomodifytags,
				nls.builtins.code_actions.impl,
				nls.builtins.formatting.goimports,
				nls.builtins.formatting.gofumpt,
				nls.builtins.formatting.prettier,
				nls.builtins.diagnostics.cmake_lint,
				require("none-ls.diagnostics.cpplint"),
			})
		end,
	},
}
