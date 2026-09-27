# UI Audit

## 质量画像原文快照

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

## 页面 / 视口矩阵

### 证据分级

| 级别 | 页面 / 范围 | 证据要求 |
|---|---|---|
| key | 看板、任务列表、任务详情抽屉、新建 / 编辑任务表单、全局 shell（顶栏 + 侧栏 + Toast 容器） | desktop light、desktop dark、375px light，以及与本范围相关的关键状态截图；布局尺寸用 DOM 断言 |
| derived | 仪表盘、我的任务 / 被阻塞、回收站、安全审计、登录 / 登出、全局错误 / Toast | 复用 key 页面与 primitive 证据；每个范围至少补一张代表态或一条自动化测试；不重复四组合截图 |
| tested-only | 登录锁定、权限拒绝、服务端错误、并发冲突 | 以 HTTP / 服务层测试和一条可读输出证据为准；不在共享服务上真实爆破或制造锁定 |

“key / derived / tested-only” 是本轮证据分级，不是生产性降级；所有业务功能仍由全量测试回归。Deferred 页面为无：没有页面被排除出契约，只是证据强度按风险分层。


| 页面 / 流程 | desktop light | desktop dark | 375px light | 必查状态 |
|---|---|---|---|---|
| 仪表盘（derived） | 已有 `final-dashboard.png` | 代表态 | 代表态 | loading、empty、图表 hover / focus |
| 看板 | 已有多张证据 | 待补 | 待补 | loading、空列、拖拽、溢出提示、键盘滚动 |
| 任务列表 | 已有证据 | 待补 | 已有 `final-list-375.png` | loading、空结果、分页、筛选无命中 |
| 我的任务 / 被阻塞（derived） | 复用列表态 | 代表态 | 代表态 | empty、无权限、筛选 |
| 任务详情抽屉 | 已有 `control-baseline-detail.png` | 待补 | 待补 | 属性编辑、invalid、子任务、依赖、评论、loading、删除确认 |
| 新建 / 编辑任务 | 已有旧证据 | 待补 | 待补 | empty、filled、invalid、disabled、submitting |
| 登录 / 登出（derived） | 有运行日志 | 代表态 | 代表态 | anonymous、authenticated、错误口令；锁定用独立测试库构造 |
| 回收站（derived） | 有代码路径 | 代表态 | 代表态 | empty、恢复、结构关联确认 |
| 安全审计（derived） | 有代码路径 | 代表态 | 代表态 | empty、权限拒绝、时间线 |
| 全局 Toast / Error | 有零散证据 | 待补 | 待补 | info、success、warn、error、undo、遮挡检查 |

## 业务语义回归锚点

- 以当前全量自动化测试（控制基线修复后为 265 个）作为业务语义不回归的最低门。
- 交付前额外手工走查：建单 → 看板流转 → 详情编辑 → 评论 → 跨项目移动 → 回收站恢复。
- 登录锁定只在独立临时数据库中用失败登录构造，不在当前 `0.0.0.0` 服务上试探口令。
- UI 改动不得改变 API 契约、角色权限、任务状态机或数据持久化语义。

## 组件清单

### 基础控件 primitive

| 组件 | 现状 | 契约重点 |
|---|---|---|
| Button | 有 `btn`、variant、size，但尺寸规则刚补 | variant × size × state 全矩阵；同类区域同高 |
| IconButton | `icon-btn` | 尺寸、aria-label、hover / focus / disabled |
| Input | `.input` | regular / dense 高度、invalid、disabled、readonly、focus |
| Select | `.select` / `.select-sm` | 与 Input 同高；箭头位置在 light / dark 一致 |
| Textarea | `.textarea` | 最小高、resize、line-height、错误态 |
| Field | label + hint + error | label 关联、错误位置与间距一致 |
| Checkbox | 原生 + label | touch 尺寸、focus、disabled |
| ActionLink | `foot-link` / `foot-btn` / `link-btn` / `inline-edit` 多套 | hover 用背景 / 颜色，不默认 underline；焦点一致 |

### 复合组件

| 组件 | 现状 | 契约重点 |
|---|---|---|
| Chip / filter chip | 已有 | pressed、hover、focus、disabled、移除按钮 |
| Badge / status pill | 已有 | 语义色、长文本、边框 |
| Card | task card / KPI / panel 多种 | padding、hover、focus、dragging |
| Modal | 已有 | focus trap、footer 对齐、scrim、Esc |
| Drawer | 已有 | focus 归还、滚动、sticky header/footer |
| Toast | 已有 | 分栈、遮蔽、undo、error 常驻 |
| EmptyState | 已有 | 行动邀请、图标、下一步 |
| ErrorState | 已有 | 可重试、错误码不泄内部 |
| Skeleton | 已有 | 形状与最终布局稳定 |
| Table / List row | 已有宽窄两态 | 375px 不逐字断行、长文本防御 |

## 状态矩阵

| 状态 | Button | Input / Select | ActionLink | Card / Row | Modal / Drawer | Toast |
|---|---|---|---|---|---|---|
| default | 必查 | 必查 | 必查 | 必查 | 必查 | 必查 |
| hover | 必查 | N/A | 必查 | 必查 | scrim / close | N/A |
| active | 必查 | N/A | 必查 | drag / drop | N/A | N/A |
| focus-visible | 必查 | 必查 | 必查 | 必查 | trap / restore | close |
| disabled / readonly | 必查 | 必查 | 必查 | N/A | N/A | N/A |
| invalid / error | danger variant | border + message | N/A | error state | confirmation | error toast |
| loading | submit disabled | search spinner | N/A | skeleton | saving | pending |
| empty | N/A | placeholder | N/A | empty state | N/A | N/A |
| success | primary feedback | saved | N/A | updated card | close / refresh | success |
| dark | 必查 | 必查 | 必查 | 必查 | 必查 | 必查 |
| 375px / coarse | 40px 目标 | 40px 目标 | 40px 目标 | reflow | full-width | full-width |

## 已确认缺口

1. **缺少单一 UI contract 真相源**：控件尺寸、间距、状态和页面证据分散在 CSS、测试与截图目录中。
2. **ActionLink 有多套实现**：`foot-link`、`foot-btn`、`link-btn`、`inline-edit` 语义相近但规则不完全一致。
3. **页面 / 状态证据不完整**：dark、375px、loading、invalid、disabled、权限拒绝等仍有缺口。
4. **测试偏局部静态规则**：已有控件高度与 underline 检查，但未覆盖全部 primitive × state × viewport。
5. **评审缺少显式 UI contract 输入**：design 角色有通用检查项，但任务画像未强制提供 token / primitive / state / viewport 契约。
6. **CSS 仍有很多 inline layout**：`style="display:flex..."` 分散在 JS 中，难以保证一致性与可维护性。

## 外部参照

- Design Tokens Community Group：token 的价值是在设计工具、代码库和平台间可靠共享视觉语言，支持规模化设计决策与互操作。采信“token 是跨工具 / 代码的单一视觉语言载体”。
- Radix Primitives：底层可访问组件可作为 design system 基础，支持增量采用，并处理 ARIA、焦点管理与键盘导航。采信“primitive + 可访问行为 + 增量采用”；不采信“必须引入依赖”。

## Options Considered

| Option | Cost | Risk | Reversibility | Time | Complexity |
|---|---|---|---|---|---|
| A. 继续修用户可见缺陷 | 低 | 高：问题会持续再现 | 高 | 0.5d | 低 |
| B. token + primitive 契约 + 状态证据矩阵 + skill 制度化 | 中 | 中：需迁移既有 CSS / 测试 | 高：增量替换 | 2-3d | 中 |
| C. 全量重构为组件库 / CSS Modules | 高 | 高：功能回归与交付周期拉长 | 低 | 1w+ | 高 |

**推荐：Option B。** 它把根因收敛为可执行契约与证据，不引入运行时依赖，也不做无关重构。
