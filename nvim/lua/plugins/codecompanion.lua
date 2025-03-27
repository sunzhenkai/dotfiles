return {
	"olimorris/codecompanion.nvim",
	-- enabled = false,
	config = function()
		require("codecompanion").setup({
			opts = {
				language = "简体中文",
			},
			adapters = {
				deepseek = function()
					-- get deepseek api key from environment variable
					local api_key = os.getenv("OPENAI_API_KEY")
					if not api_key then
						vim.notify("OPENAI_API_KEY not set！", vim.log.levels.ERROR)
						return
					end
					return require("codecompanion.adapters").extend("deepseek", {
						env = {
							api_key = api_key,
						},
						schema = {
							model = {
								default = "deepseek-chat",
							},
						},
					})
				end,
			},
			strategies = {
				chat = {
					adapter = "deepseek",
				},
				inline = {
					adapter = "deepseek",
				},
			},
		})
	end,
	dependencies = {
		"nvim-lua/plenary.nvim",
		"nvim-treesitter/nvim-treesitter",
	},
}
