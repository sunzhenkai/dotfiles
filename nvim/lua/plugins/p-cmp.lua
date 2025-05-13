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
		optional = true,
		dependencies = {
			"hrsh7th/cmp-nvim-lsp",
			"hrsh7th/cmp-buffer",
			"hrsh7th/cmp-path",
			"rafamadriz/friendly-snippets",
			"garymjr/nvim-snippets",
		},
		opts = function(_, opts)
			opts.sorting = opts.sorting or {}
			opts.sorting.comparators = opts.sorting.comparators or {}
			table.insert(opts.sorting.comparators, 1, require("clangd_extensions.cmp_scores"))
		end,
	},
}
