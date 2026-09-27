# UI 质量制度化闭环

- slug: ui-quality-institutionalization
- status: completed
- created: 2026-09-27
- updated: 2026-09-27
- completed: 2026-09-27
- handed-off: 2026-09-27

## 目标

- 用 delivery-loop normal 模式治本修复当前任务管理平台的 UI 一致性问题，并把可复用的 UI 质量契约制度化到共享 skill；共享 skill 不写入项目专有名称、页面、类名或固定像素。

## 非目标

- 不重写前端框架，不引入运行时第三方依赖。
- 不做视觉风格改版，不改业务功能语义。
- 不把当前项目的 32px / 36px、具体页面名或 CSS 类名写进共享 skill。
- 不自动 commit / push / 部署。

## 交付结论

- 2026-09-27 闭环完成：foundation / composites / pages / skills 四个子 change 全部归档；driver 归档。
- 项目终态：306/306 tests OK（含 icon primitive 批次新增 7 条契约测试）；contrast 明暗全过；ui_evidence 40 张 complete。
- 机制产物：CSS 三层（tokens/components/app）、`.icon` SVG primitive（禁裸字符与 emoji 码点，静态门钉住）、表单同高契约（禁类型特例高度）、`--form-actions-gap` 间距 token、emoji 静态门、ModalAndIconContract 浏览器契约。
- skill 产物（通用措辞，patch 可逆向）：role-based-reviewer design.md 第 9 节；task-wizard quality-profile UI 四问 + task-wizard-goal spec Requirement；delivery-loop 增量验证协议 + eval case。
- 后续缺陷批次（弹窗高度 / icon 三问）同样按机制修复并归入本子 change 的 pages / skills 归档记录。

## 归档后修复（同日）

- 用户指出弹窗输入框 36px 观感偏高，质疑「两档密度是设计内」的结论。复核确认是 bug，根因有三：
  1. foundation 切片把遗留默认值 36px 直接升格为「常规档」token，档位边界围着遗留值画，而非从密度推导；
  2. 验证循环论证——静态门钉 token 值、浏览器契约断言「控件跟 token」，两道门都验「实现符合实现自己」，档位本身永远验不到；
  3. 评审把契约当真相源，核对符合性而不问档位是否成立。
- 修复：收敛为单档 `--control-h: 32px`，删除 `--control-h-sm`（CSS 13 处迁移、静态门改为「禁止第二档 token」断言、突变测试改注入真错值 36px）；实测弹窗控件与顶栏按钮全部 32px、间距 16px。
- 全量 306/306 OK，contrast 达标，40 张截图重新生成。
- skill gap 沉淀：role-based-reviewer patch `20260927-171900-density-tier-justification`（61 单档优先多档需比例依据 / 62 禁止遗留值升格为档位）；静态门新增 density 检查与 reverse。
- 教训：一致性契约只能验证「实现是否符合约定」，不能验证「约定本身是否成立」；档位/数值类设计决策必须有可追溯推导，否则测试越全，循环论证越牢固。

## 现状

- 交付项目：`/tmp/agent-delivery-quality/task-platform-20260927T011500`。
- 证据目录：`/tmp/agent-delivery-quality/task-platform-evidence-20260927T011500`。
- 用户指出的系统性问题：任务详情控件高度不一致、顶栏按钮高度不一致、管理入口 hover 下划线过期，且细节问题未被评审覆盖。
- 已做过一次局部修复：控件 32px 基线、hover 去 underline，265/265 tests OK；但这是症状修复，尚未形成完整 UI 设计系统与制度化验收。
- 外部参照事实：
  - Design Tokens Community Group 说明 design tokens 用于在设计工具、代码库和平台间可靠共享视觉语言，目标是规模化设计决策与互操作（https://www.designtokens.org/）。
  - Radix Primitives 文档说明底层可访问组件可作为 design system 基础，支持增量采用，并处理 ARIA、焦点管理与键盘导航等难细节（https://www.radix-ui.com/primitives/docs/overview/introduction）。
- 共享 skill 已有 delivery-loop / taskflow 的质量画像、五维 rubric、三层回归与 normal 输入模式；缺的是 UI contract 的通用字段与微观 design review 清单。

## 方案

- 完成判据：当前平台的 UI 控件、交互状态和视觉证据由可复用 design system 约束；同区域控件尺寸与状态一致；关键页面具备 light / dark / desktop / 375px 证据与自动化契约测试；product/design/engineer 复核无 P0/P1；共享 skill 只沉淀通用 UI contract 与评审规则，无项目专有信息，并通过 patch 与静态门验证。

### 质量画像原文快照

```text
受众与场景:
  技术团队成员在本地任务管理平台中浏览看板 / 列表 / 详情，创建与维护任务，使用回收站与安全审计；维护者需要通过可复用 UI 契约持续保证一致性。

规模与运行假设:
  现有本地单机应用；覆盖 desktop、375px 窄屏、light / dark、细指针与粗指针；不改变后端并发与数据规模假设；运行时零第三方依赖保持不变。

页面/主流程:
  1. 看板 / 列表 / 仪表盘浏览与筛选。
  2. 任务详情查看与属性编辑。
  3. 新建 / 编辑任务表单。
  4. 登录 / 登出与顶栏操作。
  5. 回收站与安全审计管理入口。
  6. 375px 与深色模式下的关键页面复核。

角色底线:
  product: 不改变业务功能与信息架构；页面、组件、入口和状态可被完整盘点；用户报告的视觉问题不再依赖人工逐个发现。
  design: 建立 tokens 与 component primitives；同区域控件尺寸、边框、字号、焦点、hover、disabled 状态一致；间距与密度成体系；light / dark 与 desktop / 375px 均可检查；不使用突兀下划线作为常规 hover。
  engineer: 不引入运行时依赖；静态契约测试与 DOM 尺寸断言覆盖关键区域；全量测试与对比度审计通过；运行证据写入 /tmp 证据目录；共享 skill 修改走 patch 协议且可逆向校验。

显式降级:
  无。本轮不降低上述默认期望；如实现中出现新降级，必须先标 pending 并停下等用户确认。
```

- 显式降级原文快照：`无。pending 降级为 0。`
- 事实：design tokens 与底层可访问 primitives 是公开设计系统实践；当前项目已具备 CSS、静态测试、对比度审计和浏览器验证基础。
- 假设：无需引入 Radix 代码依赖；只借鉴“token + primitive + state contract”的结构，项目继续使用原生 HTML/CSS/JS。
- 步骤：
  1. UI Audit — 盘点页面、组件、状态、视口与现有缺陷；验证：矩阵覆盖所有关键页面与状态。
  2. Design System — 定义 tokens、component primitives、layout 与 interaction state contract；验证：文档可执行且无重复真相源。
  3. 控件迁移 — 统一 Button / Input / Select / Textarea / Field / action link；验证：DOM 尺寸断言与静态契约测试。
  4. 状态与证据 — 覆盖 hover / focus / disabled / invalid / empty / error 与 light / dark / desktop / 375px；验证：截图矩阵和浏览器 console。
  5. 制度化 — 将通用 UI contract、normal 派发上下文和 design micro-review 规则沉淀到共享 skill；验证：patch、eval、spec / 静态门与隐私扫描。
- 阻塞点：无。
- 坑：不要把项目专有内容写进共享 skill；不要复制 taskflow rubric 数字口径；不要为视觉重构牺牲既有 265 个测试；不要让 benchmark 隔离规则影响 normal 派发上下文。

## 进展

- 2026-09-27：完成 UI Audit、项目 design system 与 skill 制度化设计。首轮三角色评审 5 个 Major；补证据分级、组件契约、CSS 工具链、inline layout 与 DOM 断言后复核通过，无 P0/P1。

## 决策

- D1 采纳：Option B「token + primitive 契约 + 状态证据矩阵 + 共享 skill 制度化」——它治根因且可增量落地，不做全量框架重构。
- D1 取舍：接受项目内显式像素与页面契约；共享 skill 只保留通用 UI contract。接受 Playwright 作为开发期测试依赖，运行时仍零第三方依赖。
- D1 带进实现的未决：无。证据按 key / derived / tested-only 分级，不构成生产性降级。
- D1 回退：项目侧按 CSS 文件与测试提交分组还原；skill 侧按 patch 逆向还原；任务设计保留审计。

## 交接

- driver: `ui-quality-institutionalization-driver`
- 采纳方案: D1 Option B「token + primitive 契约 + 状态证据矩阵 + 共享 skill 制度化」
- design: `design/ui-audit.md`、`design/design-system.md`、`design/institutionalization.md`
- 质量画像 / 显式降级原文快照: 见「方案」小节；显式降级为无，pending=0。
- proposal: `openspec/changes/ui-quality-institutionalization-driver/proposal.md`

## 未决问题

- [x] normal 还是 benchmark —— normal；这是真实交付修复，不是能力盲测。
- [x] 是否引入第三方 UI 库 —— 不引入；只借鉴公开 design token / primitive 实践。
- [x] 共享 skill 是否写项目像素或页面名 —— 禁止；只写通用 UI contract。

## 下一步

- taskflow：从 driver 第一个未勾项继续；进度只认 driver 与子 change checkbox。
