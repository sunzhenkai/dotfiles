# 前端 Next.js 路径：从单行备注升级为可落地的一等路径

- target: agents/skills/project-init
- mode: update
- patch: 20260924-012843-nextjs-support
- risk: medium
- status: proposed

## Intent

优化 `project-init` 对 Next.js 的支持：此前 Next.js 只是「特定场景再用」的单行备注，reference 里没有可执行的骨架命令、目录约定与 align 清单，agent 遇到 Next 需求只能即兴发挥。本次给 `frontend` 栈补一条**与默认 Vite 并列的 Next.js 路径**，覆盖：

1. **选路入口**：在 `SKILL.md` 明确 `frontend` 有 Vite（默认）与 Next 两条路径、按需求/点名选一条、禁止并存；分层表 Build 与 Framework 行补 Next。
2. **落地 reference**：`references/frontend.md` 拆分 Vite / Next 两节，新增 Next 路径的官方命令（`create-next-app` + `shadcn init`）、各层落地表（含 `"use client"` 边界、Route Handler 健康检查）、目录约定、冒烟命令、align 对照。
3. **工具命令优先不变**：Next 路径同样先跑官方 CLI（`create-next-app` / `shadcn init`），不足才手搓；缺 `pnpm` 先问。
4. **测试锁定**：契约测试补 Next 路径断言，并锁「Next 相关词不进 frontmatter」。

非目标：不改 Python 与前端默认栈；不改星级口径；不新增第二个栈 id；不动 Vite 路径既有行为；不引入 Pages Router / JavaScript 作为默认（仍按用户点名）。

## Conflict check

- 与现有「Next.js 属于特定场景再用」一致，本次只是把它从备注升级为可执行路径，不改变「默认 Vite」。
- 与 `SKILL.md` 已有「已有 Next.js 按 Next 对照、不强改回 Vite」一致，并补上「已是 Vite 也不强改 Next」。
- 不新增栈 id，符合「同一 reference 内可有多条路径」；扩展段已写明该口径。
- 与门禁 / 方案确认 / 工具命令优先 / 依赖询问无冲突。
- 保持 frontmatter description 不含框架名（渐进披露），测试同时锁这一点。

## Rationale

跨项目通用：Next.js 是高频前端需求，缺可落地路径会导致 agent 手搓 `next.config` 或与官方模板漂移。补齐官方命令、Server/Client 边界与健康检查约定后，agent 与人都能复现同一条路径，且契约测试可确定性验证。

## Files

- `agents/skills/project-init/SKILL.md` — 栈表加两条前端路径说明；前端分层表 Build / Framework 补 Next；模式与工作流、安全示例补 `create-next-app`；扩展段说明「同 reference 多路径」
- `agents/skills/project-init/references/frontend.md` — 拆 Vite / Next 两节；新增 Next.js 路径（官方入口、各层落地、目录约定、冒烟、align 对照）
- `agents/skills/project-init/tests/test_project_init_contract.py` — 新增 Next 路径断言与 frontmatter 不含 Next 的断言

## Validation

- 应用前：`git apply --check --recount` 本 patch
- 应用后：`git diff --check -- agents/skills/project-init`；`python3 -m unittest discover -s agents/skills/project-init/tests`
- frontmatter `name`/`id` 与目录名一致；引用路径存在；无隐私信息
