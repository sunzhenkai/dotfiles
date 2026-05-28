return {
	{
		"folke/sidekick.nvim",
		enabled = true,
		dependencies = {
			"nvim-treesitter/nvim-treesitter-textobjects",
		},
		-- opts = {
		-- 	nes = { enabled = false},
		-- },
		keys = {
			{
				"<leader>al",
				function()
					require("sidekick.cli").toggle()
				end,
				desc = "Sidekick Toggle CLI",
			},
		},
	},
}
