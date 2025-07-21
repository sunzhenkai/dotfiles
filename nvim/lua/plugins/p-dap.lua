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
			-- go
			"nvim-neotest/neotest-go",
		},
		opts = function(_, opts)
			opts.adapters = {
				require("neotest-gtest"),
				require("neotest-go")({
					experimental = {
						test_table = true,
					},
				}),
			}
		end,
	},
}
