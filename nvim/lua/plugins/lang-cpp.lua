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
		"Civitasv/cmake-tools.nvim",
		opts = {
			cmake_build_directory = "build",
			cmake_generate_options = { "-D", "CMAKE_EXPORT_COMPILE_COMMANDS=1" },
		},
	},
	{
		"p00f/clangd_extensions.nvim",
		lazy = true,
		config = function() end,
		opts = {
			inlay_hints = {
				inline = false,
			},
			ast = {
				--These require codicons (https://github.com/microsoft/vscode-codicons)
				role_icons = {
					type = "",
					declaration = "",
					expression = "",
					specifier = "",
					statement = "",
					["template argument"] = "",
				},
				kind_icons = {
					Compound = "",
					Recovery = "",
					TranslationUnit = "",
					PackExpansion = "",
					TemplateTypeParm = "",
					TemplateTemplateParm = "",
					TemplateParamObject = "",
				},
			},
		},
	},
	{
		"mfussenegger/nvim-lint",
		enabled = false,
		opts = {
			linters_by_ft = {
				c = { "cpplint" },
				cpp = { "cpplint" },
			},
			linters = {
				cpplint = {
					args = {
						"--filter=-legal/copyright",
						-- set line length, the default value is 80
						"--linelength=100",
					},
				},
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
