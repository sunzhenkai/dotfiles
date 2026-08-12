# Open Code Review (OCR)

[Open Code Review](https://github.com/alibaba/open-code-review) AI 代码审查 CLI（bin: `ocr`）。

## 安装

```shell
dotf ocr -i
# 或安装 + 配置
dotf ocr -ic
```

依赖 Node/npm（`sdk` 模块）。全局包：`@alibaba-group/open-code-review`。

## 配置

```shell
dotf ocr -c
```

优先通过 `ocr config set` 写入 `~/.opencodereview/config.json`（非整目录软链）；无 `ocr` 时回退合并仓库模板：

| 键 | 值 | 说明 |
|----|-----|------|
| `provider` | `minimax-cn` | 国内站 `api.minimaxi.com`（与 Codex/Pi 同源） |
| `model` | `MiniMax-M3` | 默认审查模型 |
| `providers.minimax-cn.model` | `MiniMax-M3` | OCR 要求 providers 段存在 |
| `language` | `中文` | 审查意见语言 |

**不写入 API Key**：OCR 在 `providers.minimax-cn.api_key` 未设时回退环境变量 `MINIMAX_API_KEY`。

```shell
export MINIMAX_API_KEY="..."   # 与 Codex 同源；见 ~/.envrc
ocr llm test                   # 验证连通性
```

> 勿用海外站 provider `minimax`（`api.minimax.io` / `MINIMAX_GLOBAL_API_KEY`），国内 key 会 401。

## 常用命令

```shell
ocr review                              # 工作区暂存/未暂存/未跟踪变更
ocr review --from main --to HEAD        # 分支范围
ocr scan --path scripts                 # 全量文件扫描
ocr delegate preview                    # 委托模式（用编程 Agent 的 LLM，无需 OCR 配模型）
```

文档：[open-codereview.ai/docs](https://open-codereview.ai/docs)
