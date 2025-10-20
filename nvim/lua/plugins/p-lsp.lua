local dft_capabilities = vim.lsp.protocol.make_client_capabilities()
dft_capabilities.general = dft_capabilities.general or {}
dft_capabilities.general.positionEncodings = { "utf-16" }

return {
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
				clangd = {
					filetypes = { "c", "cpp", "objc", "objcpp", "cuda", "hpp" },
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
				},
				gopls = {
					cmd = { "gopls", "-remote=auto" }, -- Use gopls daemon mode for performance
				},
			},
			setup = {},
		},
	},
}
