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
	-- ray-x/navigator.lua
	{
		"ray-x/navigator.lua",
		dependencies = {
			{ "hrsh7th/nvim-cmp" },
			{ "nvim-treesitter/nvim-treesitter" },
			{ "ray-x/guihua.lua", run = "cd lua/fzy && make" },
			{
				"ray-x/go.nvim",
				event = { "CmdlineEnter" },
				ft = { "go", "gomod" },
				build = ':lua require("go.install").update_all_sync()',
			},
			{
				"ray-x/lsp_signature.nvim", -- Show function signature when you type
				event = "VeryLazy",
				config = function()
					require("lsp_signature").setup()
				end,
			},
		},
		config = function()
			require("go").setup()
			require("navigator").setup({
				lsp_signature_help = true, -- enable ray-x/lsp_signature
				lsp = { format_on_save = true },
			})

			vim.api.nvim_create_autocmd("FileType", {
				pattern = { "go" },
				callback = function()
					-- CTRL/control keymaps
					vim.api.nvim_buf_set_keymap(0, "n", "<C-i>", ":GoImport<CR>", {})
					-- conflict with vim shotcut
					-- vim.api.nvim_buf_set_keymap(0, "n", "<C-b>", ":GoBuild %:h<CR>", {})
					vim.api.nvim_buf_set_keymap(0, "n", "<C-t>", ":GoTestPkg<CR>", {})
					vim.api.nvim_buf_set_keymap(0, "n", "<C-c>", ":GoCoverage -p<CR>", {})

					-- Opens test files
					vim.api.nvim_buf_set_keymap(0, "n", "A", ":lua require('go.alternate').switch(true, '')<CR>", {}) -- Test
					vim.api.nvim_buf_set_keymap(
						0,
						"n",
						"V",
						":lua require('go.alternate').switch(true, 'vsplit')<CR>",
						{}
					) -- Test Vertical
					vim.api.nvim_buf_set_keymap(
						0,
						"n",
						"S",
						":lua require('go.alternate').switch(true, 'split')<CR>",
						{}
					) -- Test Split
				end,
				group = vim.api.nvim_create_augroup("go_autocommands", { clear = true }),
			})
		end,
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
