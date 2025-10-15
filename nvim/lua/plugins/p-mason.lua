return {
	{
		"mason-org/mason.nvim",
		opts = {
			-- https://github.com/williamboman/mason-lspconfig.nvim
			ensure_installed = {
				"prettier",
				"rust-analyzer",
				"shfmt",
				"stylua",
				"buf",
				"protolint",
				"eslint_d",
				"copilot-language-server",
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
		"mason-org/mason-lspconfig.nvim",
		enabled = true,
		dependencies = {
			"mason-org/mason.nvim",
			"neovim/nvim-lspconfig",
		},
		opts = {
			ensure_installed = {
				"lua_ls", -- Lua
				"ruff", -- Python
				"gopls", -- Go
				"rust_analyzer", -- Rust
				"clangd", -- C/C++
				"buf_ls", -- protobuf
				"ts_ls", -- typescript
			},
			automatic_installation = true,
			automatic_enable = true,
		},
	},
}
