return {
	{ "saghen/blink.cmp", enabled = false },
	{ "nvimtools/none-ls.nvim", enabled = false },
	{
		-- https://github.com/yetone/avante.nvim
		"yetone/avante.nvim",
		enabled = false,
		-- if you want to build from source then do `make BUILD_FROM_SOURCE=true`
		-- ⚠️ must add this setting! ! !
		build = vim.fn.has("win32") ~= 0
				and "powershell -ExecutionPolicy Bypass -File Build.ps1 -BuildFromSource false"
			or "make",
		event = "VeryLazy",
		version = false, -- Never set this value to "*"! Never!

		-- build = "powershell -ExecutionPolicy Bypass -File Build.ps1 -BuildFromSource false" -- for windows
		dependencies = {
			"nvim-lua/plenary.nvim",
			"MunifTanjim/nui.nvim",
			--- The below dependencies are optional,
			"nvim-mini/mini.pick", -- for file_selector provider mini.pick
			"nvim-telescope/telescope.nvim", -- for file_selector provider telescope
			"hrsh7th/nvim-cmp", -- autocompletion for avante commands and mentions
			"ibhagwan/fzf-lua", -- for file_selector provider fzf
			"stevearc/dressing.nvim", -- for input provider dressing
			"folke/snacks.nvim", -- for input provider snacks
			"nvim-tree/nvim-web-devicons", -- or echasnovski/mini.icons
			"zbirenbaum/copilot.lua", -- for providers='copilot'
			{
				-- support for image pasting
				"HakonHarnes/img-clip.nvim",
				event = "VeryLazy",
				-- WARN: this plugin will leading to slow pasting operation
				enabled = false,
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
		---@module 'avante'
		---@type avante.Config
		opts = {
			provider = "qianwen",
			auto_suggestions_provider = "qianwen_nes",
			dual_boost = {
				enabled = false,
			},
			providers = {
				deepseek = {
					__inherited_from = "openai",
					api_key_name = "DEEPSEEK_API_KEY",
					endpoint = "https://api.deepseek.com/v1",
					model = "deepseek-coder",
					extra_request_body = {
						temperature = 0,
						max_completion_tokens = 8192, -- Increase this to include reasoning tokens (for reasoning models)
						--reasoning_effort = "medium", -- low|medium|high, only used for reasoning models
					},
				},
				qianwen = {
					__inherited_from = "openai",
					api_key_name = "QWEN_API_KEY",
					endpoint = "https://dashscope.aliyuncs.com/compatible-mode/v1",
					model = "qwen3-coder-plus",
					timeout = 30000, -- Timeout in milliseconds, increase this for reasoning models
					extra_request_body = {
						temperature = 0,
						max_completion_tokens = 8192, -- Increase this to include reasoning tokens (for reasoning models)
						--reasoning_effort = "medium", -- low|medium|high, only used for reasoning models
					},
				},
				-- next edit suggestions
				qianwen_nes = {
					__inherited_from = "openai",
					api_key_name = "QWEN_API_KEY",
					endpoint = "https://dashscope.aliyuncs.com/compatible-mode/v1",
					model = "qwen3-coder-flash",
					timeout = 30000, -- Timeout in milliseconds, increase this for reasoning models
					extra_request_body = {
						temperature = 0,
						max_completion_tokens = 8192, -- Increase this to include reasoning tokens (for reasoning models)
						--reasoning_effort = "medium", -- low|medium|high, only used for reasoning models
					},
				},
			},
			behaviour = {
				auto_suggestions = true,
			},
			input = {
				provider = "snacks",
				provider_opts = {
					-- Additional snacks.input options
					title = "Avante Input",
					icon = " ",
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
