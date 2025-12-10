-- local dft_capabilities = vim.lsp.protocol.make_client_capabilities()
-- dft_capabilities.general = dft_capabilities.general or {}
-- dft_capabilities.general.positionEncodings = { "utf-16" }

return {
	-- neovim/nvim-lspconfig
	{
		"neovim/nvim-lspconfig",
		event = "LazyFile",
		dependencies = {
			"mason-org/mason.nvim",
			"mason-org/mason-lspconfig.nvim",
			"hrsh7th/cmp-nvim-lsp",
			-- c/c++
			"p00f/clangd_extensions.nvim",
		},
		opts = {
			servers = {
				clangd = {
					filetypes = { "c", "cpp", "objc", "objcpp", "cuda", "hpp" },
					cmd = {
						"clangd",
						"--background-index",
						"--clang-tidy",
						"--header-insertion=iwyu",
						"--completion-style=detailed",
						"--function-arg-placeholders",
						"--fallback-style=google",
						"--log=error",
					},
				},
				gopls = {
					cmd = { "gopls", "-remote=auto" }, -- Use gopls daemon mode for performance
					settings = {
						gopls = {
							-- 性能优化设置
							-- 限制诊断更新频率，减少 CPU 占用（延迟 500ms）
							diagnosticsDelay = "500ms",
							-- 禁用静态检查以提升性能（如果需要可以改为 true）
							staticcheck = false,
							-- 限制诊断范围，禁用耗时的检查
							diagnostics = {
								staticcheck = false,
								unusedparams = false,
							},
							-- 限制工作目录范围，避免索引整个系统
							directoryFilters = { "-**/node_modules", "-**/.git", "-**/vendor" },
							-- 减少并行度，降低 CPU 占用（默认是 CPU 核心数）
							maxParallelism = 4,
							-- 限制代码补全的预算时间
							completionBudget = "100ms",
							-- 禁用占位符，提升补全速度
							usePlaceholders = false,
							-- 使用简化的悬停信息
							hoverKind = "SynopsisDocumentation",
							-- 使用模糊匹配，更快
							symbolMatcher = "fuzzy",
							-- 限制索引范围，只索引当前模块
							expandWorkspaceToModule = false,
						},
					},
				},
			},
			setup = {},
		},
	},
}
