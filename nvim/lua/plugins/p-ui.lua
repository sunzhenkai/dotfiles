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
				return string.format("%s·%s", to.raise(to.id), to.lower(to.ordinal))
			end
			return opts
		end,
	},
	{
		"ellisonleao/gruvbox.nvim",
		priority = 1010,
		config = function()
			require("gruvbox").setup()
			vim.o.background = "light"
			vim.cmd([[colorscheme gruvbox]])
		end,
		opts = {},
	},
	{
		"romgrk/barbar.nvim",
		enabled = false,
		dependencies = {
			"nvim-tree/nvim-web-devicons", -- patched fonts support
			"lewis6991/gitsigns.nvim", -- display git status
		},
		init = function()
			vim.g.barbar_auto_setup = false
		end,
		config = function()
			local barbar = require("barbar")

			barbar.setup({
				clickable = true, -- Enables/disables clickable tabs
				tabpages = true, -- Enable/disables current/total tabpages indicator (top right corner)
				insert_at_end = true,
				icons = {
					button = "",
					buffer_index = true,
					filetype = { enabled = true },
					visible = { modified = { buffer_number = false } },
					gitsigns = {
						added = { enabled = true, icon = "+" },
						changed = { enabled = true, icon = "~" },
						deleted = { enabled = true, icon = "-" },
					},
				},
			})

			-- key maps
			local map = vim.api.nvim_set_keymap
			local opts = { noremap = true, silent = true }

			-- Move to previous/next
			map("n", "<A-,>", "<Cmd>BufferPrevious<CR>", opts)
			map("n", "<A-.>", "<Cmd>BufferNext<CR>", opts)
			-- Re-order to previous/next
			map("n", "<A-<>", "<Cmd>BufferMovePrevious<CR>", opts)
			map("n", "<A->>", "<Cmd>BufferMoveNext<CR>", opts)
			-- Goto buffer in position...
			map("n", "<A-1>", "<Cmd>BufferGoto 1<CR>", opts)
			map("n", "<A-2>", "<Cmd>BufferGoto 2<CR>", opts)
			map("n", "<A-3>", "<Cmd>BufferGoto 3<CR>", opts)
			map("n", "<A-4>", "<Cmd>BufferGoto 4<CR>", opts)
			map("n", "<A-5>", "<Cmd>BufferGoto 5<CR>", opts)
			map("n", "<A-6>", "<Cmd>BufferGoto 6<CR>", opts)
			map("n", "<A-7>", "<Cmd>BufferGoto 7<CR>", opts)
			map("n", "<A-8>", "<Cmd>BufferGoto 8<CR>", opts)
			map("n", "<A-9>", "<Cmd>BufferGoto 9<CR>", opts)
			map("n", "<A-0>", "<Cmd>BufferLast<CR>", opts)
			-- Pin/unpin buffer
			map("n", "<A-p>", "<Cmd>BufferPin<CR>", opts)
			-- Close buffer
			map("n", "<A-c>", "<Cmd>BufferClose<CR>", opts)
			map("n", "<A-b>", "<Cmd>BufferCloseAllButCurrent<CR>", opts)
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
