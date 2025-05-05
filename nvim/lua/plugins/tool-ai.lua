return {
	{ "stevearc/dressing.nvim", enabeled = true },
	{
		-- https://github.com/yetone/avante.nvim
		"yetone/avante.nvim",
		event = "VeryLazy",
		version = false, -- Never set this value to "*"! Never!
		-- if you want to build from source then do `make BUILD_FROM_SOURCE=true`
		build = "make",
		-- build = "powershell -ExecutionPolicy Bypass -File Build.ps1 -BuildFromSource false" -- for windows
		dependencies = {
			"nvim-treesitter/nvim-treesitter",
			"stevearc/dressing.nvim",
			"nvim-lua/plenary.nvim",
			"MunifTanjim/nui.nvim",
			--- The below dependencies are optional,
			"echasnovski/mini.pick", -- for file_selector provider mini.pick
			"nvim-telescope/telescope.nvim", -- for file_selector provider telescope
			"hrsh7th/nvim-cmp", -- autocompletion for avante commands and mentions
			"ibhagwan/fzf-lua", -- for file_selector provider fzf
			"nvim-tree/nvim-web-devicons", -- or echasnovski/mini.icons
			{
				-- support for image pasting
				-- WARN: will lead to slow pasting operation
				"HakonHarnes/img-clip.nvim",
				enabled = false,
				event = "VeryLazy",
				opts = {
					-- recommended settings
					default = {
						embed_image_as_base64 = false,
						prompt_for_file_name = false,
						drag_and_drop = {
							insert_mode = true,
						},
						-- required for Windows users
						use_absolute_path = true,
					},
				},
			},
			{
				-- Make sure to set this up properly if you have lazy=true
				"MeanderingProgrammer/render-markdown.nvim",
				opts = {
					file_types = { "markdown", "Avante" },
				},
				ft = { "markdown", "Avante" },
			},
		},
	},
	{
		"yetone/avante.nvim",
		enabled = true,
		opts = {
			provider = "qianwen",
			auto_suggestions_provider = "qianwen",
			dual_boost = {
				enabled = false,
			},
			vendors = {
				deepseek = {
					__inherited_from = "openai",
					api_key_name = "DEEPSEEK_API_KEY",
					endpoint = "https://api.deepseek.com/v1",
					model = "deepseek-coder",
				},
				qianwen = {
					__inherited_from = "openai",
					api_key_name = "QWEN_API_KEY",
					endpoint = "https://dashscope.aliyuncs.com/compatible-mode/v1",
					model = "qwen-coder-plus-latest",
					timeout = 30000, -- Timeout in milliseconds, increase this for reasoning models
					temperature = 0,
					max_completion_tokens = 8192, -- Increase this to include reasoning tokens (for reasoning models)
					--reasoning_effort = "medium", -- low|medium|high, only used for reasoning models
				},
			},
		},
	},
	{
		"olimorris/codecompanion.nvim",
		enabled = false,
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
	},
}
