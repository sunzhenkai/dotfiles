return {
	{
		"mason-org/mason.nvim",
		opts = {
			-- https://github.com/williamboman/mason-lspconfig.nvim
			ensure_installed = {
				"black",
				"pyright",
				"debugpy",
			},
		},
	},
	{
		"nvim-treesitter/nvim-treesitter",
		opts = { ensure_installed = { "ninja", "rst", "python" } },
	},

	-- neovim/nvim-lspconfig
	{
		"neovim/nvim-lspconfig",
		opts = {
			servers = {
				pyright = {
					disableLanguageServices = false,
					disableOrganizeImports = false,
					typeCheckingMode = "strict",
					python = {
						analysis = {
							django = true,
						},
					},
				},
			},
		},
	},
}
