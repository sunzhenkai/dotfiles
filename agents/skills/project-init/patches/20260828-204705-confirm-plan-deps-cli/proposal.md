# 方案确认、缺依赖询问、工具命令优先

- target: agents/skills/project-init
- patch: 20260828-204705-confirm-plan-deps-cli
- risk: medium
- status: proposed

## Intent

改变动手前的工作流，不改分层表与默认栈：

1. 选层后形成**最终方案**，展示并等待用户明确确认；未确认不得创建目录、改依赖或改文件。
2. 方案选定后**检查依赖**（包管理器与该栈官方 CLI）；缺失则**询问是否补齐**，不得默默全局安装或未经询问切换回退。
3. `init` **优先借助官方工具命令**生成骨架；CLI 缺失先问补齐，仍不可用且用户同意才手写最小壳。

非目标：不改 Python/前端分层与星级；不自动装机；不扩大可执行远程脚本的范围。

## Conflict check

- 与现有「无 `uv` 则 venv」「无 `pnpm` 则 npm」的静默回退冲突，改为先问。
- 与「不要为了脚手架去全局安装包管理器，除非用户要求」一致，并落实为询问补齐。
- 与 align「确认后再改」同构；init 补上同等的方案确认。
- FastAPI 仍无独立 create 模板：骨架以 `uv init` / `uv add` 为工具命令，不是退回纯手搓。

## Rationale

跨项目可执行：先确认方案、再问缺失依赖、再跑官方 CLI，避免 agent 静默换栈或手搓与官方模板漂移的树。合同测试锁住关键用语。

## Files

- `agents/skills/project-init/SKILL.md` — 工作流插入方案确认与依赖检查；包管理器改为询问后补齐/回退
- `agents/skills/project-init/references/python-api.md` — 工具命令优先；`uv` 缺失先问
- `agents/skills/project-init/references/frontend.md` — 工具命令优先；`pnpm` 缺失先问
- `agents/skills/project-init/tests/test_skill_contract.py` — 锁住确认 / 补齐 / CLI 优先

## Validation

- 应用前：`git apply --check --recount` 本 patch
- 应用后：`git diff --check -- agents/skills/project-init`；`python3 -m unittest discover -s agents/skills/project-init/tests`
- frontmatter `name`/`id` 与目录名一致；引用路径存在；无私有信息
