---
id: project-init
name: project-init
description: >-
  按约定脚手架创建或对齐项目（v1：Python API 与前端）。
  仅在用户显式要求初始化项目、创建项目脚手架、scaffold，或要求把已有项目架构向本 skill 对齐时使用。
  不要用于日常写功能、装机、克隆仓库或启动服务。
---

# Project Init

面向用户的输出默认使用简体中文。命令、路径、代码、包名与既成术语保持原文。

按约定脚手架**创建**新项目，或把**已有项目**对齐到本 skill 的架构约定。v1 只实现 Python API 与前端两栈；其他语言/架构未提供 reference 时不得即兴发明。已支持栈内的具体框架按分层表与需求选择，不得无视需求套死一套。

## 门禁（强制）

未过门禁不得创建目录、改依赖、改配置或重写目录结构。最终方案未经用户确认、缺失依赖未经询问，同样不得动手。

**算触发（必须同时满足「显式」）：**

- 用户点名本 skill / `project-init`，或明确说要**初始化项目**、**创建项目脚手架**、**scaffold 新项目**。
- 用户明确要求把**已有项目/已有架构向本 skill 对齐**（例如「按 project-init 对齐」「对齐 FastAPI 脚手架」）。

**不算触发：**

- 日常加功能、改 bug、加组件、加 API 接口。
- 装机/配环境（交给对应环境 skill）、克隆仓库、启动/停止服务。
- 顺口的 `git init`、`npm init`、建单个文件、在已有应用里加一个页面。
- 用户只说「新写一个函数/页面/接口」，没有要求初始化或对齐项目架构。

不确定时先问一句是否要走本 skill，得到明确肯定前当普通编码任务处理。

## 非目标

- 不实现业务功能、产品页面或领域模型；脚手架只含能跑通的空壳与健康检查。
- 不装机、不改系统包、不克隆远程仓、不代替服务启停。
- 不自动 commit / push；不写入密钥、真实 `.env` 值、内部 URL。
- 不把未支持的栈临时写成「官方默认」；要扩栈须改本 skill 的 reference，不在一次脚手架会话里发明新约定。
- 不把「特定场景再用 / 需要再用 / 用户点名」的备选预装进默认脚手架。
- 不在用户未确认时默默切换包管理器，或为脚手架擅自全局安装工具。

## 模式

| 模式 | 何时 | 行为 |
|------|------|------|
| `init` | 目标目录不存在、为空，或只有 git 占位（如 `README` / `.gitignore` / `.git`） | 方案确认后用官方工具命令创建，再套本 skill 约定 |
| `align` | 目标已有实质源码或依赖清单 | 对照约定出缺口报告，**确认后再改** |

目录已有另一套框架（如 Flask、Vue、CRA）时：**禁止**在 align 里偷偷换成默认栈。先报告不兼容，只有用户明确要求迁移才进入迁移（仍先给计划再改）。已有 Django 且用户未要求迁移：按 Django 路径对照，不要强改 FastAPI。已有 Next.js 视为前端「特定场景」变体：按 Next 对照，不要强改回 Vite。

一次会话只服务**一个**目标根。前后端都要时，先问清是两个根还是 monorepo 子目录，再分别套对应 reference。

## 栈（v1）

未说明栈时：像 API 服务的 Python → `python-api`（Web Framework 默认 FastAPI）；像 SPA/站点 UI 的前端 → `frontend`。Python 但不是 API（CLI / 库 / 脚本）→ 告知 v1 未覆盖，停止，不擅自改用 Flask/FastAPI。

**按需求选层（强制）**：先根据已确认需求对照分层表选择具体库，形成最终方案并确认后再执行。用户点名的库优先于表中的默认/推荐，并在摘要标明偏离。需求不足以下决定的层：采用「必选」「默认」；「推荐」在用户未拒绝时装入；「需要…再用」「特定场景再用」「用户点名」一律不预装。禁止凭偏好把默认 FastAPI 换成 Django，或把已有 Django 在 align 中改成 FastAPI。

| 栈 id | 默认 | 先读 |
|-------|------|------|
| `python-api` | 分层见下表；纯 API 默认 FastAPI | [python-api.md](references/python-api.md) |
| `frontend` | 分层见下表；命令与目录见 [frontend.md](references/frontend.md) | [frontend.md](references/frontend.md) |

### Python 分层

建议列决定 init 是否默认装入，见 [python-api.md](references/python-api.md) 的映射。

| 层 | 选择 | Agent 友好度 | 建议 |
|----|------|-------------|------|
| Web Framework | FastAPI | ⭐⭐⭐⭐⭐ | 默认 |
| Web Framework | Django | ⭐⭐⭐⭐ | 特定场景再用（Admin / MTV / Django 全家桶） |
| Web Framework | Flask | ⭐⭐⭐ | 用户点名 |
| Web Framework | Litestar | ⭐⭐⭐ | 用户点名 |
| API / Validation | Pydantic | ⭐⭐⭐⭐⭐ | 必选（非 Django 路径） |
| API / Validation | OpenAPI | ⭐⭐⭐⭐⭐ | 必选 |
| API / Validation | SQLModel | ⭐⭐⭐ | 需要模型与 schema 一体再用 |
| ORM | SQLAlchemy | ⭐⭐⭐⭐⭐ | 默认（非 Django） |
| ORM | Django ORM | ⭐⭐⭐⭐ | 随 Django |
| ORM | Tortoise ORM | ⭐⭐ | 用户点名 |
| Async / Runtime | asyncio · uvicorn · anyio | — | FastAPI / Litestar 默认 |
| Background Jobs | Celery · Dramatiq · ARQ | — | 需要后台任务再用 |
| Testing | pytest · httpx | — | 必选 |
| Testing | Playwright | — | 需要浏览器 E2E 再用 |
| Tooling | uv | — | 默认包管理 |
| Tooling | Ruff | — | 推荐 |
| Tooling | mypy / pyright | — | 推荐 |

### 前端分层

建议列决定 init 是否默认装入，见 [frontend.md](references/frontend.md) 的映射。

| 层 | 选择 | Agent 友好度 | 建议 |
|----|------|-------------|------|
| Language | TypeScript | ⭐⭐⭐⭐⭐ | 必选 |
| UI Framework | React | ⭐⭐⭐⭐⭐ | 必选 |
| Build | Vite | ⭐⭐⭐⭐⭐ | 默认 |
| CSS | Tailwind CSS | ⭐⭐⭐⭐⭐ | 默认 |
| UI | shadcn/ui | ⭐⭐⭐⭐⭐ | 强烈推荐 |
| Server State | TanStack Query | ⭐⭐⭐⭐⭐ | 推荐 |
| Client State | Zustand | ⭐⭐⭐⭐⭐ | 推荐 |
| Validation | Zod | ⭐⭐⭐⭐⭐ | 推荐 |
| Form | React Hook Form | ⭐⭐⭐⭐ | 需要表单再用 |
| API Contract | OpenAPI / Zod | ⭐⭐⭐⭐⭐ | 强烈推荐 |
| E2E | Playwright | ⭐⭐⭐⭐⭐ | 必选 |
| Unit | Vitest | ⭐⭐⭐⭐⭐ | 推荐 |
| Framework | Next.js | ⭐⭐⭐⭐ | 特定场景再用 |

包管理器：用户指定优先；否则 Python 默认 `uv`，前端默认 `pnpm`。工具或包管理器缺失时列入依赖缺口，**询问是否补齐**（安装该工具，或改用已说明的回退：Python 为 venv + pip，前端为 npm）。未确认不得自行切换，也不得为脚手架擅自全局安装。

## 工作流

1. **过门禁**，判定 `init` 或 `align`。目标路径未给则询问，不在无关 cwd 里下手。
2. **收集输入**（缺一则问，不猜）：目标路径、栈、项目名、包管理器（若会写进锁文件）。`init` 还要确认目标可写且不会覆盖已有工程。需求特征会影响选层时（Admin、后台任务、模型与 schema 一体、浏览器 E2E、SSR 等）缺则问，不猜。
3. **形成最终方案并确认**：只加载对应 reference，按需求选层，列出最终方案（模式、目标路径、各层选择与原因、拟用官方工具命令、将写入的约定、冒烟命令）。**展示给用户并等待明确确认**。未确认不得创建目录、改依赖或改文件。用户改需求则回到选层，不要边做边改方案。
4. **检查依赖**：方案选定并确认之后、动手之前，检查该方案所需的工具命令是否可用（如 `uv`、`python3`、`pnpm`/`npm`、`node`，以及该栈官方 create/init CLI）。列出缺失项，**询问是否补齐**。用户同意后再安装或启用已确认的回退；用户拒绝则停止或改用其指定替代。不得默默全局安装，不得未经询问切换包管理器。项目框架包跟随官方 CLI / `uv add` / 包管理器安装，不要预先手搓 lockfile。
5. **执行**：`init` **优先借助该栈官方工具命令**（见各 reference，如 `uv init`、`django-admin startproject`、`pnpm create vite`、`shadcn init`），再用本 skill 约定补配置、空布局、健康检查、`.env.example`、`.gitignore`、README。官方 CLI 可用时禁止手搓完整项目树。CLI 缺失：先按步骤 4 问是否补齐；仍不可用且用户明确同意后，才写最小可运行壳。`align`：只改已确认项，补齐同样走官方工具命令；不重写业务代码来「看起来更像模板」。不要启动长期 dev server。冒烟见各 reference。
6. **交付摘要**（见下）。不 commit。

## 安全

- 目标必须是用户指定或确认过的路径；禁止写到家目录根、系统目录或其他仓库。
- `init` 遇到已有源码：改为 `align` 或停止，禁止覆盖。
- 不执行未审查的远程脚本；只用该栈官方文档中的 create/init CLI（如 `uv init`、`django-admin startproject`、`create vite`、`shadcn init`）。初始化应优先跑这些命令，而不是先手写同等文件。
- `.env.example` 只放变量名与无害示例值；真实密钥不入库。

## 交付摘要

完成后用简短列表告诉用户：

- 模式（`init` / `align`）与目标路径
- 方案是否已经用户确认
- 依赖检查：缺什么、是否补齐、用了什么回退
- 实际采用的栈与是否偏离默认（含 Python / 前端各层：装了什么、因何需求、故意没装什么）
- 关键路径（如何启动、健康检查 URL 或 build / test 命令）
- 改了哪些文件（align 必列）
- 明确没做的事（业务、部署、CI、commit）

## 扩展

新增栈：增加 `references/<stack-id>.md`，并在上表加一行。reference 必须写清官方脚手架命令、目录约定、默认依赖、冒烟命令、align 对照清单。无 reference 的栈 = 未支持。
