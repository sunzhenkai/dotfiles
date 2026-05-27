return {
	-- {
	-- 	"mason-org/mason.nvim",
	-- 	opts = {
	-- 		-- https://github.com/williamboman/mason-lspconfig.nvim
	-- 		ensure_installed = {
	-- 			"black",
	-- 			"pyright",
	-- 			"debugpy",
	-- 		},
	-- 	},
	-- },
	-- {
	-- 	"nvim-treesitter/nvim-treesitter",
	-- 	opts = { ensure_installed = { "ninja", "rst", "python" } },
	-- },

	-- neovim/nvim-lspconfig
	{
		"neovim/nvim-lspconfig",
		opts = {
			servers = {
				pyright = {
					-- initializationOptions (协议层，非 settings)
					init_options = {
						disableLanguageServices = false,
						disableOrganizeImports = false,
					},
					settings = {
						python = {
							analysis = {
								typeCheckingMode = "strict",
								djangoSettings = true,
							},
						},
					},
				},
			},
		},
	},
}
