return {
  {
    "neovim/nvim-lspconfig",
    opts = {
      servers = {
        -- 默认 single-file：不用 .git 当 root，避免 ~/work 这类巨型库全量扫 md 超时。
        -- 需要跨文件 wiki/引用时，在该笔记库根目录放 .marksman.toml 即可。
        marksman = {
          root_markers = { ".marksman.toml" },
        },
        gopls = {
          settings = {
            gopls = {
              -- gopls 0.18+ 的 modifier（signature/number 等）与 LazyVim workaround
              -- 注入的客户端 legend 不一致，会触发 semantic_tokens.lua 报错。
              semanticTokens = false,
            },
          },
          capabilities = (function()
            local caps = vim.tbl_deep_extend(
              "force",
              vim.lsp.protocol.make_client_capabilities(),
              require("cmp_nvim_lsp").default_capabilities()
            )
            if caps.textDocument then
              caps.textDocument.semanticTokens = nil
            end
            return caps
          end)(),
        },
      },
      setup = {
        -- 阻止 LazyVim go extra 注册错误的 semanticTokens workaround
        gopls = function() end,
      },
    },
  },
}
