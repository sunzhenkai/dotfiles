-- install with yarn or npm
return {
	{
		"mason-org/mason.nvim",
		opts = { ensure_installed = { "markdownlint-cli2", "markdown-toc" } },
	},
	{
		"nvim-treesitter/nvim-treesitter",
		opts = { ensure_installed = { "markdown", "markdown_inline" } },
	},
	{ "iamcco/markdown-preview.nvim" },
	{ "MeanderingProgrammer/render-markdown.nvim" },
}
