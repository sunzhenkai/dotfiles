# 创建 project-init

- target: agents/skills/project-init
- patch: 20260828-201317-create-skill
- risk: high
- status: proposed

## Intent

新增公开共享 Skill `project-init`：按约定脚手架**创建**新项目，或把**已有项目架构向本 skill 对齐**。

触发（必须显式）：

- 初始化项目 / 创建项目脚手架 / scaffold / 点名 `project-init`
- 要求已有架构向本 skill 对齐

非目标：日常写功能、装机、克隆仓库、启动服务、未点名时的 `git init`/`npm init`、即兴发明未支持的语言栈。

frontmatter `description` 只写触发与范围（Python API / 前端），**不罗列具体框架**。

v1 框架只支持两栈：

- Python API：默认 Django + django-rest-framework（细节在 reference，不进 description）
- 前端：按分层表落地（TS/React 必选，Vite/Tailwind 默认，shadcn 与 OpenAPI/Zod 强烈推荐，Query/Zustand/Zod/Vitest 推荐，Playwright 必选；RHF 要表单再用，Next.js 特定场景再用）

行为要点：官方 CLI 优先；init 不覆盖已有工程；align 先缺口报告再改；异栈不自动迁移；已有 Next.js 不改回 Vite。

## Conflict check

- `dotf-init`：机器/用户环境初始化，不是项目脚手架。
- `repo-manager`：多仓 clone/sync，不创建语言项目树。
- `service-manager`：已有项目的进程启停，不负责 scaffold。
- `project-spec-mirror` / `taskflow` / `task-design`：规格与交付生命周期，不写脚手架代码。
- 仓库内无同名 Skill。职责重叠通过门禁与非目标隔开。

## Rationale

跨项目可复用：触发门禁、两模式、官方脚手架、建议列映射、align 不迁移异栈，均不绑定特定仓库。description 保持短触发语，避免过期框架清单污染发现层。合同测试锁住「description 不含框架名」与前端分层表。

## Files

- `agents/skills/project-init/SKILL.md` — 门禁、模式、栈表、前端分层、工作流
- `agents/skills/project-init/references/python-api.md` — Django + DRF
- `agents/skills/project-init/references/frontend.md` — 分层落地、Vite 默认、Next 场景
- `agents/skills/project-init/tests/test_skill_contract.py` — 合同测试

## Validation

- 应用前：`git apply --check --recount` 本 patch
- 应用后：`git diff --check -- agents/skills/project-init`；`python3 -m unittest discover -s agents/skills/project-init/tests`
- frontmatter `name`/`id` 与目录名一致；引用路径存在；无私有信息
