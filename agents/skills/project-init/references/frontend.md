# 前端

本 reference 只在栈为 `frontend` 时读取。分层与建议以 `SKILL.md` 前端表为准；这里只写怎么落地。用户点名 Vue / CRA 等则不要套本文件。

**工具命令优先**：先跑 `pnpm create vite` / `create-next-app` / `shadcn init`。官方 CLI 可用时不要手写 `package.json`、Vite 或 Tailwind 配置来「等价生成」。CLI 缺失时先按 `SKILL.md` 询问是否补齐。

## 建议 → init 行为

| 建议 | init | align 缺口 |
|------|------|------------|
| 必选 | 必须具备，缺则不算完成 | 列为应补 |
| 默认 | 未指定替代时采用 | 已用等价替代则记录偏差，不强制改回 |
| 强烈推荐 | 默认装入；用户明确拒绝才省略 | 列为应补（除非用户已拒绝） |
| 推荐 | 默认装入；用户明确拒绝才省略 | 列为建议补，确认后再改 |
| 需要表单再用 | **不预装** | 仅当项目已有表单、或用户要加表单时才提议 |
| 特定场景再用 | **不作为默认**；仅用户点名该场景 | 已采用则按该场景对照，不改回默认 |

Next.js 属于「特定场景再用」：仅当用户明确要 SSR / RSC / SEO / App Router 等时用官方 `create-next-app`（TypeScript），再按 shadcn 的 Next 指南接入。不要与 Vite 并存。其余层（TS、React、Tailwind、shadcn、Query、Zustand、Zod、Playwright、Vitest）仍然适用，Build 改由 Next 承担。

## 官方入口（默认：Vite）

包管理器：`pnpm` > `npm`（用户指定优先）。无 `pnpm` 时列入缺失，**询问是否补齐**（安装 `pnpm`，或改用 npm）；未确认不得自行切换。在**最终方案已确认、依赖已检查**的空目标（或仅 git 占位）下：

```bash
pnpm create vite . --template react-ts
# 或：npm create vite@latest . -- --template react-ts
```

若 CLI 拒绝非空目录：先确认里面只有安全占位文件；可用官方文档中的 force 类参数，或在临时空目录生成再移入用户确认过的文件。禁止覆盖已有 `src/`。

然后按 **shadcn/ui 当前 Vite 指南**初始化（会安装 Tailwind 并写 `components.json`）。优先非交互：

```bash
pnpm dlx shadcn@latest init -d
# 或：npx shadcn@latest init -d
```

`-d` / `--defaults` 以当时 CLI 为准；若标志变更，改用官方文档的非交互等价参数，不要手搓与 shadcn 漂移的 Tailwind 配置。

```bash
pnpm dlx shadcn@latest add button
```

空壳：极简占位（标题 + 一个 shadcn `Button`）即可，不要一次装整套组件。

## 各层落地（默认 Vite 路径）

在 Vite + shadcn 之上按表补齐。包名用当时官方包，不在本文件钉死次版本。

| 层 | 做什么 |
|----|--------|
| Language / UI Framework | `react-ts` 模板；禁止改回 JavaScript |
| Build | 保留 Vite；用户未点名 Next 时不要换成 Next |
| CSS / UI | 跟随 `shadcn init`；`src/components/ui/` 只放 shadcn 生成物 |
| Server State | 安装 `@tanstack/react-query`；在根部挂 `QueryClientProvider`（空配置，不写业务 query） |
| Client State | 安装 `zustand`；`src/stores/` 只放可扩展的空 store 骨架，不放领域字段 |
| Validation | 安装 `zod`；与 API Contract 共用 |
| Form | 不安装 `react-hook-form`，除非用户要表单 |
| API Contract | 安装 `zod`。有 OpenAPI 文档（本地 `openapi.json` / 用户给出的 spec）时用官方 codegen（如 `openapi-typescript`）生成客户端，Zod 做运行时校验；**没有 spec 时不要虚构一整份 OpenAPI**。建 `src/lib/api/`：`client.ts` 薄封装 + 一个与健康检查对应的 Zod schema 作为合同示例 |
| E2E | 安装 `@playwright/test`，写 `playwright.config.ts` 与一条访问根路径的 smoke spec。init **不**默认下载浏览器二进制；README 写明 `playwright install` 后再跑 E2E |
| Unit | 安装 `vitest`（及官方 React 测试搭档，如 jsdom + Testing Library）；能跑通一条渲染占位的测试即可 |

不要默认再加 React Router、MUI、Ant Design 等。用户点名则加，并在摘要标明偏离。

## 目录约定

以 Vite + shadcn 官方结果为底，再加本表目录（不要另造 `features/` 分层，除非用户要求）：

```text
<project-root>/
  package.json
  tsconfig.json
  tsconfig.app.json          # 以 CLI 实际产出为准
  vite.config.ts
  vitest.config.ts           # 或并入 vite.config.ts，以官方推荐为准
  playwright.config.ts
  components.json
  index.html
  README.md
  .gitignore
  e2e/
    smoke.spec.ts
  src/
    main.tsx                 # QueryClientProvider
    App.tsx
    index.css
    test/
      setup.ts               # 若 Vitest 需要
    lib/
      utils.ts
      api/
        client.ts
        health.ts            # Zod schema 示例
    stores/
      app-store.ts
    components/ui/
```

- 路径别名 `@/` 必须在 tsc 与 Vite 中都有效。
- 业务组件放 `src/components/`（`ui/` 留给 shadcn）。
- 不要提交 `node_modules/`。`.gitignore` 含 `.env`、`.env.local`、Playwright 产物。

README 写清：`dev`、`build`、`vitest`、Playwright（含先 `playwright install`）。不要写虚构部署环境。

## 冒烟（init 必做）

```bash
pnpm build
pnpm exec vitest run
```

无 `pnpm` 且方案已确认改用 npm 时：`npm run build` 与 `npx vitest run`。失败则修复后再结束。不要后台挂起 `dev`，也不要默认跑 Playwright（缺浏览器）。

## align 对照

已是 Vite + React + TS，或用户确认保留的 Next.js 时，按分层表逐项看，确认后再补：

| 层 | 期望 |
|----|------|
| Language | TypeScript |
| UI Framework | React |
| Build | Vite（Next 场景则为 Next，不改回 Vite） |
| CSS | Tailwind，且与 shadcn 一致 |
| UI | `components.json` + `src/components/ui/` |
| Server State | TanStack Query 已接入根 Provider |
| Client State | Zustand 已有 stores 约定 |
| Validation | Zod 已用于契约或表单 |
| Form | 有表单才需要 React Hook Form；无表单不装 |
| API Contract | OpenAPI codegen 或等价 Zod schema；禁止手写无校验的散落 `fetch` 作为唯一合同 |
| E2E | Playwright 配置 + 至少一条 smoke |
| Unit | Vitest 可运行 |

Vue / CRA / Svelte / 无打包静态页：报告「栈不兼容」，**不改代码**，除非用户明确要求迁移并确认计划。仅缺 shadcn/Tailwind、其余已是 Vite+React+TS 时，确认后按官方 `shadcn init` 补齐。
