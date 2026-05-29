return {
  {
    "neovim/nvim-lspconfig",
    opts = {
      servers = {
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
