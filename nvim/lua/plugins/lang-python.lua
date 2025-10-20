return {
	-- {
	-- 	"linux-cultist/venv-selector.nvim",
	-- 	dependencies = {
	-- 		"neovim/nvim-lspconfig",
	-- 		"mfussenegger/nvim-dap",
	-- 		"mfussenegger/nvim-dap-python", --optional
	-- 		"nvim-telescope/telescope.nvim",
	-- 	},
	-- 	lazy = false,
	-- 	branch = "main",
	-- 	keys = {
	-- 		{ ",v", "<cmd>VenvSelect<cr>" },
	-- 	},
	-- 	opts = {
	-- 		-- Your settings go here
	-- 		name = "venv",
	-- 		auto_refresh = true,
	-- 		search_venv_managers = true,
	-- 		search_workspace = true,
	-- 	},
	-- },
	{
		"mason-org/mason.nvim",
		opts = {
			-- https://github.com/williamboman/mason-lspconfig.nvim
			ensure_installed = {
				"black",
				"pyright",
				"debugpy",
			},
		},
	},
	{
		"nvim-treesitter/nvim-treesitter",
		opts = { ensure_installed = { "ninja", "rst", "python" } },
	},

	-- neovim/nvim-lspconfig
	{
		"neovim/nvim-lspconfig",
		opts = {
			servers = {
				-- pyright = {
				-- 	disableLanguageServices = false,
				-- 	disableOrganizeImports = false,
				-- 	typeCheckingMode = "strict",
				-- 	python = {
				-- 		analysis = {
				-- 			django = true,
				-- 		},
				-- 	},
				-- },
			},
			setup = {
				-- 	pyright = function()
				-- 		require("lazyvim.util").lsp.on_attach(function(client, _)
				-- 			if client.name == "pyright" then
				-- 				-- disable hover in favor of jedi-language-server
				-- 				client.server_capabilities.hoverProvider = false
				-- 			end
				-- 		end)
				-- 	end,
			},
		},
	},
}
