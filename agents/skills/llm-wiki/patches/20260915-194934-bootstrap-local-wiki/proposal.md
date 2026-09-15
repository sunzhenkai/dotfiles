# 从 llmwiki 提炼本地文档知识整理 skill

- target: agents/skills/llm-wiki
- patch: 20260915-194934-bootstrap-local-wiki
- risk: high
- status: proposed

## Intent

新增共享 skill `llm-wiki`：让 agent 在本地 Markdown 工作区整理、摄入、查询、重组并检查知识 wiki。

触发：用户点名 `llm-wiki` / 整理知识 / 维护 wiki / ingest 本地文档 / 查询或 lint 知识库。

非目标：不运行 llmwiki 服务或 MCP；不写项目 spec 镜像；不探索业务源码；不改 `raw/`；不自动 commit / sync。

## Conflict check

- `project-spec-mirror`：软件功能契约镜像，不是通用知识 wiki。
- `dotf-code-explore`：代码理解与仓库知识，不是 typed wiki。
- 源仓库 `llmwiki` 的 MCP skill 依赖服务与 SQLite；本 skill 把同一套布局与不变量落到文件系统工具。
- 无重名 `agents/skills/llm-wiki/`。

## Rationale

Karpathy / LLM Wiki 的价值在「摄入时编译、wiki 常驻累积」，不依赖桌面应用。抽出 typed 目录、实体/概念边界、先搜再写、仅追加 log 与确定性 lint，可在任意本地文档库复用，并可用脚本验证。

用户已明确要求从该仓库提取一个基于本地文档的 skill，构成本次创建批准。

## Files

- `agents/skills/llm-wiki/SKILL.md`：阶段路由、绑定、不变量
- `agents/skills/llm-wiki/agents/openai.yaml`：展示名
- `agents/skills/llm-wiki/references/layout.md`：canonical 布局与 init
- `agents/skills/llm-wiki/references/page-types.md`：类型、模板、命名
- `agents/skills/llm-wiki/references/ingest.md`：摄入流程
- `agents/skills/llm-wiki/references/lint.md`：检查码与修复
- `agents/skills/llm-wiki/scripts/lint_wiki.py`：确定性 lint 与 index 重建
- `agents/skills/llm-wiki/tests/test_llm_wiki_contract.py`
- `agents/skills/llm-wiki/tests/test_lint_wiki.py`

## Validation

- `git apply --check --recount` 本 patch
- 应用后 `git diff --check -- agents/skills/llm-wiki`
- `python3 -m pytest -q agents/skills/llm-wiki/tests`
- frontmatter `name` 与目录名一致；无隐私路径；不引入 MCP 运行时依赖
