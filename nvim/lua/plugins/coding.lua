return {
	-- numToStr/Comment.nvim
	{
		"numToStr/Comment.nvim",
		opts = {
			-- add any options here
		},
	},
	-- folke/trouble.nvim
	{
		"folke/trouble.nvim",
		-- opts will be merged with the parent spec
		opts = { use_diagnostic_signs = true },
	},
	-- danymat/neogen
	{
		"danymat/neogen",
		config = function()
			require("neogen").setup({ snippet_engine = "luasnip" })
		end,
		keys = {
			{
				"<Leader>znc",
				"<cmd>lua require('neogen').generate({ type = 'class' })<CR>",
				desc = "Generate Class Documentation",
			},
			{
				"<Leader>znd",
				"<cmd>lua require('neogen').generate({ type = 'file' })<CR>",
				desc = "Generate File Documentation",
			},
			{
				"<Leader>znf",
				"<cmd>lua require('neogen').generate({ type = 'func' })<CR>",
				desc = "Generate Function Documentation",
			},
		},
		-- Uncomment next line if you want to follow only stable versions
		-- version = "*"
	},
	-- echasnovski/mini.pairs
	{
		"echasnovski/mini.pairs",
		event = "VeryLazy",
		opts = {
			modes = { insert = true, command = true, terminal = false },
			-- skip autopair when next character is one of these
			skip_next = [=[[%w%%%'%[%"%.%`%$]]=],
			-- skip autopair when the cursor is inside these treesitter nodes
			skip_ts = { "string" },
			-- skip autopair when next character is closing pair
			-- and there are more closing pairs than opening pairs
			skip_unbalanced = true,
			-- better deal with markdown code blocks
			markdown = true,
		},
		config = function(_, opts)
			LazyVim.mini.pairs(opts)
		end,
	},
	-- folke/lazydev.nvim
	{
		"folke/lazydev.nvim",
		ft = "lua",
		cmd = "LazyDev",
		opts = {
			library = {
				{ path = "${3rd}/luv/library", words = { "vim%.uv" } },
				{ path = "LazyVim", words = { "LazyVim" } },
				{ path = "snacks.nvim", words = { "Snacks" } },
				{ path = "lazy.nvim", words = { "LazyVim" } },
			},
		},
	},
	-- code folder
	-- kevinhwang91/nvim-ufo
	{
		"kevinhwang91/nvim-ufo",
		dependencies = {
			"kevinhwang91/promise-async",
			"neovim/nvim-lspconfig",
		},
		setup = function()
			require("ufo").setup()
		end,
	},
}
