return {
	{
		"folke/snacks.nvim",
		keys = {
			{
				"<leader><space>",
				function()
					local root = vim.uv.cwd()
					local ok, manager = pcall(require, "neo-tree.sources.manager")
					if ok then
						local state = manager.get_state("filesystem")
						if state and state.path and state.path ~= "" then
							root = state.path
						end
					end
					Snacks.picker.files({ cwd = root })
				end,
				desc = "Find Files (Neo-tree Root)",
			},
			{
				"<leader>ff",
				function()
					local root = vim.uv.cwd()
					local ok, manager = pcall(require, "neo-tree.sources.manager")
					if ok then
						local state = manager.get_state("filesystem")
						if state and state.path and state.path ~= "" then
							root = state.path
						end
					end
					Snacks.picker.files({ cwd = root })
				end,
				desc = "Find Files (Neo-tree Root)",
			},
			{
				"<c-/>",
				function()
					local root = vim.uv.cwd()
					local ok, manager = pcall(require, "neo-tree.sources.manager")
					if ok then
						local state = manager.get_state("filesystem")
						if state and state.path and state.path ~= "" then
							root = state.path
						end
					end
					Snacks.terminal(nil, { cwd = root })
				end,
				mode = { "n", "t" },
				desc = "Terminal (Neo-tree Root)",
			},
			{
				"<leader>ft",
				function()
					local root = vim.uv.cwd()
					local ok, manager = pcall(require, "neo-tree.sources.manager")
					if ok then
						local state = manager.get_state("filesystem")
						if state and state.path and state.path ~= "" then
							root = state.path
						end
					end
					Snacks.terminal(nil, { cwd = root })
				end,
				desc = "Terminal (Neo-tree Root)",
			},
		},
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
					prepend_args = { "--style=file", "--fallback-style=google" },
				},
				-- python
				black = {
					prepend_args = { "--line-length", "100" },
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
			vim.g.matchup_matchparen_deferred_show_delay = 100 -- 延迟匹配显示，减少 CPU
			vim.g.matchup_matchparen_deferred_hide_delay = 500
			vim.g.matchup_matchparen_timeout = 300 -- 匹配超时（毫秒）
			vim.g.matchup_matchparen_insert_timeout = 60 -- 插入模式下更短的超时
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
			-- 在保存和读取文件时触发，保持实时反馈
			events = { "BufWritePost", "BufReadPost" },
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
			-- 注意：使用 prepend_args 追加参数，而非 args 覆盖（覆盖会丢失默认参数导致报错）
			---@type table<string,table>
			linters = {
				-- c/c++/cmake
				cpplint = {
					prepend_args = {
						"--filter=-legal/copyright,-build/include_subdir,-runtime/indentation_namespace",
						-- set line length, the default value is 80
						"--linelength=120",
					},
				},
				-- Go: 优化 golangci-lint 性能
				["golangci-lint"] = {
					-- 使用 prepend_args 追加参数，保留默认的 run/--out-format 等必要参数
					prepend_args = {
						"--timeout=60s",
					},
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
	-- code folder
	-- kevinhwang91/nvim-ufo
	{
		"kevinhwang91/nvim-ufo",
		event = "LazyFile",
		dependencies = {
			"kevinhwang91/promise-async",
			"neovim/nvim-lspconfig",
		},
		config = function()
			require("ufo").setup()
		end,
	},
}
