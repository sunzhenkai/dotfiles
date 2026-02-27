return {
	{
		"folke/snacks.nvim",
		opts = {
			terminal = {
				win = {
					style = "float",
					border = "rounded",
				},
			},
		},
	},
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
					python = { "isort", "black" },
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
			-- 只在保存时触发，大幅减少 CPU 和内存占用
			events = { "BufWritePost" },
			linters_by_ft = {
				-- c/c++/cmake
				c = { "cpplint" },
				cpp = { "cpplint" },
				-- fish
				fish = { "fish" },
				-- go: 只在保存时 lint，避免频繁触发
				go = { "golangci-lint" },
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
				-- c/c++/cmake
				cpplint = {
					args = {
						"--filter=-legal/copyright,-build/include_subdir,-runtime/indentation_namespace",
						-- set line length, the default value is 80
						"--linelength=120",
					},
				},
				-- Go: 优化 golangci-lint 性能
				["golangci-lint"] = {
					-- 使用超时避免卡死
					timeout = 10000, -- 10秒超时
					args = {
						"--fast", -- 只运行快速检查
						"--timeout=10s", -- 设置超时
					},
				},
				-- eslint_d = {
				-- 	cmd = "eslint_d",
				-- 	args = { "--stdin", "--stdin-filename", "%filepath" },
				-- 	stream = "stderr",
				-- 	ignore_exitcode = true,
				-- 	parser = require("lint.parser").from_errorformat("%f:%l:%c: %m", {
				-- 		source = "eslint_d",
				-- 		severity = vim.diagnostic.severity.WARN,
				-- 	}),
				-- },
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
}
