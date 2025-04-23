return {
	{
		"mfussenegger/nvim-dap",
		config = function() end,
	},
	{
		"alfaix/neotest-gtest",
	},
	{
		"nvim-neotest/neotest",
		dependencies = {
			"nvim-neotest/nvim-nio",
			"nvim-lua/plenary.nvim",
			"antoinemadec/FixCursorHold.nvim",
			"nvim-treesitter/nvim-treesitter",
			-- c++, gtest
			"alfaix/neotest-gtest",
		},
		opts = {
			adapters = {
				["neotest-gtest"] = {},
			},
		},
	},
}
