return {
	{ "rafamadriz/friendly-snippets" },
	{
		"garymjr/nvim-snippets",
		opts = {
			friendly_snippets = true,
		},
		dependencies = { "rafamadriz/friendly-snippets" },
	},
	{
		"hrsh7th/nvim-cmp",
		enabled = true,
		dependencies = {
			"hrsh7th/cmp-nvim-lsp",
			"hrsh7th/cmp-buffer",
			"hrsh7th/cmp-path",
			"rafamadriz/friendly-snippets",
			"garymjr/nvim-snippets",
		},
	},
}
