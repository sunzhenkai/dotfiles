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
			-- 全局诊断配置：减少 CPU 占用
			diagnostics = {
				update_in_insert = false, -- 不在插入模式更新诊断
				virtual_text = {
					spacing = 4,
					prefix = "●",
				},
			},
			servers = {
				clangd = {
					filetypes = { "c", "cpp", "objc", "objcpp", "cuda" },
					cmd = {
						"clangd",
						"--background-index",
						"--clang-tidy",
						"--header-insertion=iwyu",
						"--completion-style=detailed",
						"--function-arg-placeholders",
						"--fallback-style=google",
						"--log=error",
						-- "-j=4", -- 限制后台索引并发数
						"--pch-storage=memory", -- PCH 存储在内存中（更快但要注意内存）
						"--background-index-priority=low", -- 后台索引低优先级
					},
				},
				gopls = {
					cmd = { "gopls", "-remote.listen.timeout=0" },
					settings = {
						gopls = {
							-- 性能优化，减少 CPU 占用
							diagnosticsDelay = "500ms",
							-- staticcheck = false,
							-- 限制工作目录范围，避免索引大目录
							directoryFilters = {
								"-**/node_modules",
								"-**/.git",
								"-**/vendor",
								"-**/third_party",
								"-**/.cache",
								"-**/bin",
							},
							-- 减少并行度，降低 CPU 占用
							-- maxParallelism = 2,
							-- 限制代码补全的预算时间
							-- completionBudget = "200ms",
							-- 禁用占位符，提升补全速度
							-- usePlaceholders = false,
							-- 使用简化的悬停信息
							-- hoverKind = "SynopsisDocumentation",
							-- 保留有用的 codelens，禁用耗时的
							-- codelenses = {
							-- 	gc_details = false,
							-- 	generate = true,
							-- 	regenerate_cgo = false,
							-- 	test = true,
							-- 	tidy = true,
							-- 	upgrade_dependency = false,
							-- 	vendor = false,
							-- },
							-- 限制索引范围，只索引当前模块
							-- expandWorkspaceToModule = false,
							-- 使用模糊匹配（比 CaseSensitive 更省 CPU）
							symbolMatcher = "fuzzy",
							-- 限制内存密集型分析
							-- analyses = {
							-- 	fieldalignment = false,
							-- 	shadow = false,
							-- 	unusedparams = false,
							-- 	unusedwrite = false,
							-- 	nilness = true, -- 保留空指针检查（重要）
							-- },
							-- 保留自动导入和深度补全（编码体验重要）
							completeUnimported = true,
							deepCompletion = true,
							-- 语义 token 优化
							semanticTokens = true,
							-- 内存优化：使用 gopls 内置的 gc
							memoryMode = "DegradeClosed", -- 对关闭的文件降级内存使用
						},
					},
				},
			},
			setup = {},
		},
	},
}
