return {
	-- williamboman/mason.nvim
	{
		"williamboman/mason.nvim",
		opts = {
			-- https://github.com/williamboman/mason-lspconfig.nvim
			ensure_installed = {
				"cmake-language-server",
				"cmakelint",
				-- "clangd",
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
		enabled = true,
	},
}
