return {
	-- nvim-treesitter/nvim-treesitter
	{
		"nvim-treesitter/nvim-treesitter",
		opts = { ensure_installed = { "cmake", "cpp", "c", "make" } },
	},
	-- williamboman/mason.nvim
	{
		"williamboman/mason.nvim",
		opts = {
			-- https://github.com/williamboman/mason-lspconfig.nvim
			ensure_installed = {
				"cmake-language-server",
				"cmakelint",
				"clangd",
				"codelldb",
				"clang-format",
				"cpplint",
			},
		},
	},
	{
		"neovim/nvim-lspconfig",
		-- dependencies = {
		-- 	"p00f/clangd_extensions.nvim",
		-- },
		opts = {
			servers = {
				cmake = {},
				-- Ensure mason installs the server
				clangd = {
					keys = {
						{ "<leader>ch", "<cmd>ClangdSwitchSourceHeader<cr>", desc = "Switch Source/Header (C/C++)" },
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
						"--function-arg-placeholders",
						"--fallback-style=google",
					},
					init_options = {
						usePlaceholders = true,
						completeUnimported = true,
						clangdFileStatus = true,
					},
				},
			},
			setup = {
				-- clangd = function(_, opts)
				-- 	local clangd_ext_opts = LazyVim.opts("clangd_extensions.nvim")
				-- 	require("clangd_extensions").setup(
				-- 		vim.tbl_deep_extend("force", clangd_ext_opts or {}, { server = opts })
				-- 	)
				-- 	return false
				-- end,
			},
		},
	},
	-- stevearc/conform.nvim
	-- autoformat
	{
		"stevearc/conform.nvim",
		opts = {
			formatters_by_ft = {
				c = { "clang_format" },
				cpp = { "clang_format" },
			},
			formatters = {
				clang_format = {
					prepend_args = { "--style=file", "--fallback-style=LLVM" },
				},
			},
		},
	},
}
