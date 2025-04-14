return {
	{
		"williamboman/mason.nvim",
		opts = {
			-- https://github.com/williamboman/mason-lspconfig.nvim
			ensure_installed = {
				"rust-analyzer",
				"cmake-language-server",
				"lua-language-server",
				"prettier",
				"rust-analyzer",
				"shfmt",
				"stylua",
				"sonarlint-language-server",
			},
			ui = {
				icons = {
					package_installed = "✓",
					package_pending = "➜",
					package_uninstalled = "✗",
				},
			},
		},
	},
	{
		"williamboman/mason-lspconfig.nvim",
		dependencies = {
			"williamboman/mason.nvim",
		},
		opts = {
			ensure_installed = {
				"lua_ls", -- Lua
				"pylsp",
				-- "pyright", -- Python
				"gopls", -- Go
				"rust_analyzer", -- Rust
				"clangd", -- C/C++
			},
			automatic_installation = true,
		},
	},
}
