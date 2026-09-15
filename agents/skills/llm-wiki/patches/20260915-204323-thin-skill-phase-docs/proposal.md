# 下沉阶段步骤，让主文档只做路由

- target: agents/skills/llm-wiki
- patch: 20260915-204323-thin-skill-phase-docs
- risk: medium
- status: proposed

## Intent

把 `guide` / `init` / `organize` 的逐步说明从 `SKILL.md` 下沉到 `references/`，主文档只保留路由、绑定、不变量与短阶段入口。触发场景与非目标不变。不改变 lint 脚本、页面类型或写盘门禁。

## Conflict check

- 不与 `project-spec-mirror` / `dotf-code-explore` 职责重叠。
- `init` 确认门禁仍在主文档一行，完整步骤改到 `layout.md`，避免双份流程。
- `query` 仍留在主文档（步骤短，无需单独 reference）。
- 不重命名现有 `ingest.md` / `lint.md`。

## Rationale

主文档已声明按需加载，却把六个阶段步骤写全，导致每次触发都预加载操作细节。下沉后行为可从 reference 与契约测试核对，跨环境仍成立。

## Files

- `agents/skills/llm-wiki/SKILL.md` — 阶段入口改为 1～3 行；加载表指向 `organize.md`
- `agents/skills/llm-wiki/references/layout.md` — 吸收完整 `init` / `guide`
- `agents/skills/llm-wiki/references/organize.md` — 新增重组步骤
- `agents/skills/llm-wiki/agents/openai.yaml` — default_prompt 补上 `init`
- `agents/skills/llm-wiki/tests/test_llm_wiki_contract.py` — 断言步骤不在主文档重复

## Validation

- `git apply --check --recount` 本 patch
- 应用后 `git diff --check -- agents/skills/llm-wiki`
- `python3 -m pytest -q agents/skills/llm-wiki/tests`
