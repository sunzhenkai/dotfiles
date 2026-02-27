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
					cmd = { "gopls" },
					settings = {
						gopls = {
							-- 性能优化，减少 CPU 占用
							-- 增加诊断延迟，减少频繁更新
							diagnosticsDelay = "500ms",
							-- 禁用静态检查以减少 CPU
							staticcheck = false,
							-- 限制诊断范围
							diagnostics = {
								staticcheck = false,
								unusedparams = false,
							},
							-- 限制工作目录范围，避免索引大目录
							directoryFilters = {
								"-**/node_modules",
								"-**/.git",
								"-**/vendor",
								"-**/third_party",
							},
							-- 减少并行度，降低 CPU 占用
							maxParallelism = 2,
							-- 限制代码补全的预算时间
							completionBudget = "100ms",
							-- 禁用占位符，提升补全速度
							usePlaceholders = false,
							-- 使用简化的悬停信息
							hoverKind = "SynopsisDocumentation",
							-- 保留有用的 codelens，禁用耗时的
							codelenses = {
								gc_details = false,
								generate = false,
								regenerate_cgo = false,
								test = true, -- 保留 test codelens
								tidy = false,
								upgrade_dependency = false,
							},
							-- 禁用 inlay hints
							ui = {
								inlayhint = {
									enable = false,
								},
							},
							-- 限制索引范围，只索引当前模块
							expandWorkspaceToModule = false,
							-- 使用模糊匹配
							symbolMatcher = "fuzzy",
							-- 限制内存使用
							expansionTimeout = "5s",
							-- 限制内存密集型功能
							analyses = {
								fieldalignment = false,
								shadow = false,
							},
							-- 保留自动导入（编码体验重要）
							completeUnimported = true,
							-- 保留深度补全（编码体验重要）
							deepCompletion = true,
						},
					},
				},
			},
			setup = {},
		},
	},
}
