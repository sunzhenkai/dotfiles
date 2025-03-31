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
		"olexsmir/gopher.nvim",
		ft = "go",
		enabled = true,
		-- branch = "develop"
		-- (optional) will update plugin's deps on every update
		build = function()
			vim.cmd.GoInstallBinaries()
		end,
		---@type gopher.Config
		opts = {},
	},
}
