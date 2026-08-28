# Python 按需求选层，默认 FastAPI

- target: agents/skills/project-init
- patch: 20260828-204107-python-req-driven-layers
- risk: medium
- status: proposed

## Intent

改变模型行为：`python-api` 不再钉死 Django + DRF。先按已确认需求对照分层表选择框架/库，再跑脚手架。

- 触发不变：仍须显式 `project-init` / 初始化 / 对齐。
- Web Framework：纯 API 默认 FastAPI；Django 仅 Admin / MTV / Django 全家桶或用户点名；Flask、Litestar 仅用户点名。
- 其余层：Pydantic + OpenAPI 必选（非 Django）；SQLAlchemy 默认（非 Django）；pytest + httpx 必选；uv 默认；Ruff 与 mypy/pyright 推荐；SQLModel、Tortoise、后台任务、Playwright 按需，不预装。
- 非目标：不扩 v1 语言栈；不改前端「推荐 = 默认装入」语义；不在 align 里把已有 Django 强改 FastAPI。

## Conflict check

- 与当前「默认 Django + DRF、点名 FastAPI 则不要套 python-api.md」直接冲突，本 patch 就是消除该缺口：FastAPI 成为默认路径，Django 降为特定场景并保留完整落地。
- 与「无 reference = 未支持」：Flask / Litestar 写入分层表后，reference 必须给出最小官方入口，不能只列名。
- 前端分层、门禁、init/align 模式、官方 CLI 优先均保持。
- 不涉及其他 Skill 职责。

## Rationale

与已有前端分层表同构，跨项目可复用。纯 API 场景 FastAPI 为五星默认，Django 四星留给 Admin/全家桶，避免无需求时装全家桶。需求→层映射和合同测试可验证。用户已给出分层目录与星级，作为本轮具体改动依据。

## Files

- `agents/skills/project-init/SKILL.md` — 按需求选层、Python 分层表、默认 FastAPI、工作流补需求特征
- `agents/skills/project-init/references/python-api.md` — 按需求选层落地；FastAPI 默认路径；Django 特定场景；Flask/Litestar 最小路径；可选层
- `agents/skills/project-init/tests/test_skill_contract.py` — 锁住分层名、默认 FastAPI、Django 路径仍在

## Validation

- 应用前：`git apply --check --recount` 本 patch
- 应用后：`git diff --check -- agents/skills/project-init`；`python3 -m unittest discover -s agents/skills/project-init/tests`
- frontmatter `name`/`id` 与目录名一致；引用路径存在；无私有信息
