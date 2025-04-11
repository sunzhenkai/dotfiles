-- install with yarn or npm
return {
	{
		"iamcco/markdown-preview.nvim",
		cmd = { "MarkdownPreviewToggle", "MarkdownPreview", "MarkdownPreviewStop" },
		build = "cd app && yarn install",
		init = function()
			vim.g.mkdp_filetypes = { "markdown" }
		end,
		ft = { "markdown" },
	},
	{
		"williamboman/mason.nvim",
		opts = { ensure_installed = { "markdownlint-cli2", "markdown-toc" } },
	},
	{
		"neovim/nvim-lspconfig",
		opts = {
			servers = {
				marksman = {},
			},
		},
	},
	{
		"MeanderingProgrammer/render-markdown.nvim",
		opts = {
			code = {
				sign = false,
				width = "block",
				right_pad = 1,
			},
			heading = {
				sign = false,
				icons = {},
			},
			checkbox = {
				enabled = false,
			},
		},
		ft = { "markdown", "norg", "rmd", "org", "codecompanion" },
		config = function(_, opts)
			require("render-markdown").setup(opts)
			Snacks.toggle({
				name = "Render Markdown",
				get = function()
					return require("render-markdown.state").enabled
				end,
				set = function(enabled)
					local m = require("render-markdown")
					if enabled then
						m.enable()
					else
						m.disable()
					end
				end,
			}):map("<leader>um")
		end,
	},
	{
		"nvim-treesitter/nvim-treesitter",
		opts = { ensure_installed = { "markdown", "markdown_inline" } },
	},
}
