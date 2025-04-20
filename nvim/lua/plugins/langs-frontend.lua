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
	{
		"nvim-treesitter/nvim-treesitter",
		opts = {
			ensure_installed = {
				"jsdoc",
				"javascript",
				"typescript",
				"tsx",
			},
		},
	},
	{
		"nvim-treesitter/nvim-treesitter",
		opts = function(_, opts)
			-- add tsx and treesitter
			vim.list_extend(opts.ensure_installed, {
				"tsx",
				"typescript",
			})
		end,
	},
}
