return {
	{
		"akinsho/bufferline.nvim",
		enabled = true,
		version = "*",
		dependencies = "nvim-tree/nvim-web-devicons",
		keys = {
			{ "<leader>bh", "<cmd>BufferLineCyclePrev<cr>", desc = "Buffer: Prev" },
			{ "<leader>bl", "<cmd>BufferLineCycleNext<cr>", desc = "Buffer: Next" },
			{ "<leader>b[", "<cmd>BufferLineMovePrev<cr>", desc = "Buffer: Move Prev" },
			{ "<leader>b]", "<cmd>BufferLineMoveNext<cr>", desc = "Buffer: Move Next" },
		},
		opts = function(_, opts)
			opts.options = opts.options or {}
			opts.options.always_show_bufferline = true
			opts.options.separator_style = "slant"
			opts.options.numbers = function(to)
				return string.format("%s", to.ordinal)
			end
			return opts
		end,
	},
	{
		"ellisonleao/gruvbox.nvim",
		priority = 1010,
		config = function()
			require("gruvbox").setup()
			vim.o.background = "dark"
			vim.cmd([[colorscheme gruvbox]])
		end,
	},
	{
		"nvim-mini/mini.icons",
		opts = {
			file = {
				[".eslintrc.js"] = { glyph = "󰱺", hl = "MiniIconsYellow" },
				[".node-version"] = { glyph = "", hl = "MiniIconsGreen" },
				[".prettierrc"] = { glyph = "", hl = "MiniIconsPurple" },
				[".yarnrc.yml"] = { glyph = "", hl = "MiniIconsBlue" },
				["eslint.config.js"] = { glyph = "󰱺", hl = "MiniIconsYellow" },
				["package.json"] = { glyph = "", hl = "MiniIconsGreen" },
				["tsconfig.json"] = { glyph = "", hl = "MiniIconsAzure" },
				["tsconfig.build.json"] = { glyph = "", hl = "MiniIconsAzure" },
				["yarn.lock"] = { glyph = "", hl = "MiniIconsBlue" },
			},
		},
	},
	{
		"nvim-neo-tree/neo-tree.nvim",
		enabled = true,
		dependencies = {
			"nvim-lua/plenary.nvim",
			"nvim-tree/nvim-web-devicons", -- not strictly required, but recommended
			"MunifTanjim/nui.nvim",
			-- {"3rd/image.nvim", opts = {}}, -- Optional image support in preview window: See `# Preview Mode` for more information
		},
		opts = {
			commands = {
				go_to_parent_dir = function(state)
					local node = state.tree:get_node()
					require("neo-tree.ui.renderer").focus_node(state, node:get_parent_id())
				end,
			},
			window = {
				mappings = {
					-- go to parent node
					["IP"] = "go_to_parent_dir",
				},
			},
		},
	},
}
