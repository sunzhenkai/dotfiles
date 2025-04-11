return {
	{
		"williamboman/mason.nvim",
		opts = {
			ensure_installed = {
				"css-variables-language-server",
				"stylelint",
				"css-lsp",
			},
		},
	},
	{
		"williamboman/mason-lspconfig.nvim",
		opts = {
			ensure_installed = {
				"css-variables-language-server",
				"css-lsp",
			},
		},
	},
}
