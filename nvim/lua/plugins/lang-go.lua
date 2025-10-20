return {
	{
		"ray-x/go.nvim",
		ft = { "go", "gomod", "gowork", "gotmpl" },
		build = ":GoInstallBinaries", -- 安装 gofumpt、gotests、gomodifytags、impl、dlv 等
		event = { "CmdlineEnter" },
		-- 	build = ':lua require("go.install").update_all_sync()', -- if you need to install/update all binaries
		dependencies = {
			"ray-x/guihua.lua",
			"mfussenegger/nvim-dap",
			"rcarriga/nvim-dap-ui",
			"neovim/nvim-lspconfig",
			"nvim-treesitter/nvim-treesitter",
		},
		opts = {
			gofmt = "gofumpt",
			goimport = "gopls", -- 使用 gopls 管理 import
			fillstruct = "gopls",
			test_runner = "go", -- 也可用 "richgo"
			lsp_cfg = false, -- 让 LazyVim/nvim-lspconfig 管理 gopls
			lsp_keymaps = false, -- 避免 go.nvim 注入 LSP 快捷键与 LazyVim 冲突
			lsp_codelens = true,
			lsp_inlay_hints = { enable = true },
			trouble = true, -- 与 Trouble 集成（可选）
			-- DAP
			dap_debug = true,
			dap_debug_gui = true,
			dap_debug_vt = true,
		},
		keys = {
			-- { "<leader>cr", "<cmd>GoRun<cr>", desc = "Go Run" },
			-- { "<leader>cB", "<cmd>GoBuild<cr>", desc = "Go Build" },
			-- { "<leader>ct", "<cmd>GoTestFunc<cr>", desc = "Go Test Func" },
			-- { "<leader>cT", "<cmd>GoTestFile<cr>", desc = "Go Test File" },
			-- { "<leader>cc", "<cmd>GoCoverage<cr>", desc = "Go Coverage" },
			-- { "<leader>cD", "<cmd>GoDebug<cr>", desc = "Go Debug (nearest)" },
			-- { "<leader>ca", "<cmd>GoAddTag<cr>", desc = "Go Add Tag (json)" },
			-- { "<leader>cA", "<cmd>GoRmTag<cr>", desc = "Go Remove Tag" },
			-- { "<leader>ci", "<cmd>GoIfErr<cr>", desc = "Go If-Err" },
			-- { "<leader>cg", "<cmd>GoGenerate<cr>", desc = "Go Generate" },
		},
		config = function(_, opts)
			require("go").setup(opts)
			-- 自动刷新 gopls codelens
			local group = vim.api.nvim_create_augroup("GoCodelens", { clear = true })
			vim.api.nvim_create_autocmd({ "BufEnter", "InsertLeave", "CursorHold" }, {
				group = group,
				pattern = "*.go",
				callback = function()
					pcall(vim.lsp.codelens.refresh)
				end,
			})
		end,
	},
	{
		"mason-org/mason.nvim",
		opts = {
			ensure_installed = {
				-- lsp
				"gopls",
				-- debug
				"go-debug-adapter",
				"delve",
				-- formatter
				"goimports-reviser",
				"golines",
				"gofumpt",
				-- lint
				"golangci-lint",
				"golangci-lint-langserver",
				"revive",
				-- test
				"gotests",
				"gotestsum",
				-- generate
				"gomodifytags",
				"impl",
				"staticcheck",
			},
		},
	},
	-- Go symbols in telescope/coc
	{
		"ray-x/lsp_signature.nvim",
		event = "VeryLazy",
		opts = { debug = false, hint_enable = false },
	},
}
