return {
	-- mason-org/mason.nvim
	{
		"mason-org/mason.nvim",
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
			cmake_regenerate_on_save = false,
		},
	},
	-- installed by lazyvim extra feature clangd
	-- {
	-- 	"p00f/clangd_extensions.nvim",
	-- 	lazy = true,
	-- 	enabled = true,
	-- },
}
