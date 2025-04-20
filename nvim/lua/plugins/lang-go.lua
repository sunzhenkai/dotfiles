return {
	{
		"ray-x/go.nvim",
		enabled = true,
		dependencies = { -- optional packages
			"ray-x/guihua.lua",
			"neovim/nvim-lspconfig",
			"nvim-treesitter/nvim-treesitter",
		},
		config = function()
			require("go").setup()
		end,
		event = { "CmdlineEnter" },
		ft = { "go", "gomod" },
		build = ':lua require("go.install").update_all_sync()', -- if you need to install/update all binaries
	},
	{
		"williamboman/mason.nvim",
		opts = {
			ensure_installed = {
				-- lsp
				"gopls",
				-- debug
				"go-debug-adapter",
				-- "delve",
				-- formatter
				"goimports-reviser",
				"golines",
				-- lint
				"golangci-lint",
				"golangci-lint-langserver",
				-- test
				"gotests",
				"gotestsum",
				-- generate
				"gomodifytags",
				-- "impl",
			},
		},
	},
}
