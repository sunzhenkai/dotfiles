# Delivery Loop 与 UI 质量制度化：会话知识记录

> 记录性质：这是**脱敏后的知识沉淀**，不是逐字 transcript。保留可复用的流程、决策、坑和当前状态；项目路径、机器目录、内网地址、口令、端点名与私有实现细节均用占位符表示。

## 1. 一句话结论

这轮真正有效的不是“修了三个 UI 小问题”，而是验证了一条可复用闭环：

```text
短目标
→ normal / benchmark 分流
→ 质量画像 + UI contract
→ task-explore / design / decide
→ taskflow 小切片
→ normal 派发完整上下文
→ DOM / 静态 / 截图证据
→ product/design/engineer 评审
→ skill gap / implementation bug / acceptance gap 归因
→ 修复、复验、全链路验收
→ 通用经验制度化进 skill
```

关键经验：**UI 细节问题必须当成契约与证据问题处理，不能当成散点 CSS 补丁处理。**

## 2. 脱敏说明

| 占位符 | 含义 |
|---|---|
| `<REPO_ROOT>` | 当前 dotfiles / skills 仓库根目录 |
| `<SAMPLE_PROJECT>` | 临时任务管理平台项目目录 |
| `<EVIDENCE_ROOT>` | 本轮运行证据目录 |
| `<LAN_URL>` | 临时对外访问地址 |
| `<PASSWORD>` | 本地演示口令，已脱敏 |
| `<AGENT_A>` / `<AGENT_B>` | 实现 / 测试委派 agent，不记录端点名 |

不在知识层保存：

- 本机绝对路径
- 内网 IP / 端口组合
- 口令、cookie、token
- agent roster endpoint / 主机名
- 项目私有页面名、CSS 类名、固定像素值

## 3. 上游已沉淀的通用规则

本轮 UI 闭环建立在前面已经制度化的质量门之上：

1. **task-wizard 复杂档质量画像**
   - 复杂交付不能只有功能清单。
   - 必须有受众与场景、规模与运行假设、页面 / 主流程、product/design/engineer 底线、显式降级。
   - 生产性降级只能是 `pending`，用户确认后才能 `confirmed`。

2. **task-explore / taskflow 快照传递**
   - 质量画像与降级表必须原文快照传递。
   - `pending` 降级阻止 decide / handoff / 相关验收。
   - 不允许路径指针替代原文。

3. **role-based-reviewer 结构化调用**
   - 复杂档可固定 `product,design,engineer` 三角色。
   - 普通“帮我 review”不能自动多角色化。

4. **delivery-loop 双模式**
   - `normal`：实现者必须拿到相关质量上下文。
   - `benchmark`：只给目标原文与运行约束，隐藏画像 / rubric / 期望清单。
   - 普通交付不得默认盲派；盲测必须显式标记。

## 4. 本轮问题根因

用户指出的问题：

- 任务详情里的下拉框、输入框、按钮高度不一致。
- 顶栏“登出”和“新建任务”高度不一致。
- 管理入口 hover 出现下划线，视觉语言过时。
- 结论：很多 UI 细节没有被系统性覆盖。

根因不是某几个 class 写错，而是：

1. 没有 UI contract 单一真相源。
2. token / primitive / page layer 混在一处。
3. JS 里散落大量 inline layout。
4. 测试主要是功能与局部静态断言，没有 DOM 尺寸契约。
5. 证据靠零散截图，没有状态矩阵。
6. 评审清单偏宏观，没有强制检查“同区域控件尺寸 / 状态一致性 / inline magic style”。
7. normal 派发时 UI contract 没有成为必给上下文。

## 5. 最终采用的方案

采用 Option B：

```text
UI Audit
→ design tokens
→ component primitives
→ interaction state matrix
→ viewport/theme evidence matrix
→ skill 制度化
```

明确拒绝：

- 继续逐个修可见缺陷。
- 为临时项目引入运行时 UI 框架。
- 一次性重写全部 CSS。
- 把项目专有名称、页面名、类名、像素值写进共享 skill。

## 6. 可复用流程

### 6.1 UI Audit 先行

必须先盘点四张矩阵：

1. **页面矩阵**：每个页面 / 主流程。
2. **组件矩阵**：Button、Input、Select、Textarea、Field、ActionLink、IconButton、Checkbox、Chip、Badge、Card、Overlay、Toast、Empty、Error、Skeleton、Table/List。
3. **状态矩阵**：default、hover、active、focus-visible、disabled、readonly、invalid、loading、empty、error、success、dark、coarse pointer。
4. **视口矩阵**：desktop、narrow、touch、light、dark。

证据分级：

| 级别 | 用途 | 证据强度 |
|---|---|---|
| key | 核心页面 / 主流程 | desktop light、desktop dark、narrow light、相关状态截图、DOM 断言 |
| derived | 次要页面 / 列表变体 | 复用 key/primitive 证据 + 至少一张代表态或自动化测试 |
| tested-only | 后端错误、权限拒绝、锁定、并发 | HTTP / 服务层测试 + 可读输出，不硬造截图 |

### 6.2 CSS 分层契约

采用三层：

```text
tokens.css      = 只放 token，不出现选择器规则
components.css  = primitive / composite canonical rules
app.css         = 页面布局与上下文组合，不重复组件真相
```

硬规则：

- index、静态测试、contrast 工具读取同一个 stylesheet manifest。
- 后加载层可覆盖前层，但不得重复 canonical selector。
- 页面覆盖不得改 token 控制的尺寸 / 状态 / spacing。
- `@keyframes` 全局命名，只能属于一层。

### 6.3 UI contract 模板

有 UI 交付面的复杂任务，画像或设计契约至少包含：

```text
Surface inventory:
Primitive inventory:
Token policy:
Interaction states:
Viewport & theme matrix:
Evidence contract:
Migration policy:
```

缺任一项，不得进入实现；确实不适用要写“不适用 + 原因”，不能空着。

### 6.4 DOM 契约测试

静态测试只能证明“代码怎么写”，不能证明“浏览器怎么算”。需要 Playwright 类开发期工具量真实 DOM：

- 同区域控件高度一致。
- 同一行 input / select / button 同高。
- hover / focus-visible 不导致布局位移。
- coarse pointer 下可点目标达到项目 touch token。
- key 页面无失控横向溢出。
- 负路径状态能渲染错误 / 空态 / toast / 权限拒绝。

要求：

- fail closed；环境缺失不能 skip。
- 断言有阈值，例如尺寸偏差不超过 0.5px。
- 截图确认视觉，DOM 断言负责自动发现。

### 6.5 inline style 治理

不要追求“零 inline style”这种假目标。正确目标是：

- **layout 属性**必须迁到 CSS class。
- **动态值**可以保留，但要有精确 allowlist。
- allowlist 条目必须包含：文件、形状 / 选择器、允许属性、理由。
- 不允许“某文件整体放行”。
- allowlist 不能 stale，也不能 greedy。
- 静态门要做反例验证：临时注入一个违规 inline style 必须红。

本轮实际演进：

```text
66 处 style:
→ 第一批迁走 layout
→ 25 处
→ 第二批迁走静态 appearance
→ 12 处
→ 剩余主要是动态取色与动态尺寸
```

### 6.6 状态证据矩阵

截图矩阵必须可复现，不能靠手工临时截屏。

推荐 manifest 字段：

```text
file
page
viewport
color_scheme
identity / auth state
state
key_selectors
checks
console_errors
expected_console_errors
sha256
```

原则：

- 负路径触发的 HTTP 400 / 409 / 500 可能被浏览器记成 console resource error；要记录为 `expected_console_errors`，不能伪装成 0，也不能让负路径无法取证。
- 未允许 console error 或未捕获 pageerror 必须失败。
- 不能稳定触发的状态写入 `not_covered`，不要摆拍。

### 6.7 失败归因

每条 Blocker / Major 只能归三类：

| 类型 | 判据 | 处置 |
|---|---|---|
| skill gap | 规则缺失 / 矛盾，换任务仍会错 | 走 skill-upgrader patch |
| implementation bug | 规则正确，实现错了 | 修交付仓并补回归 |
| acceptance gap | 验收维度漏了 | 补验收标准 / rubric / contract |

不要把失败笼统写成“再改改”。

本轮实例：

- foundation 首轮实现 agent 提前结束：归为 implementation/delegation incomplete，不采信；随后缩小范围复派。
- browser contract 暴露窄屏顶栏横向溢出：这是 implementation bug。
- 工具暴露 toast 自动消失导致夹具竞态：这是 acceptance/test fixture gap。
- UI contract 没进共享 skill：这是 skill gap，后续要制度化。

## 7. 委派经验

### 7.1 normal 派发必须给足上下文

normal 模式实现者至少要拿到：

- 目标原文
- 质量画像或语义裁剪
- UI contract
- 本切片验收要求
- 工作目录 / 依赖 / 时间预算 / 安全边界
- 不许 commit / push / 部署 / 外发

### 7.2 任务要窄

大范围“顺手把整个系统也改了”很容易让实现 agent 提前结束或引入回归。有效拆法：

1. CSS 分层与工具同步。
2. Slice 1 primitives。
3. browser DOM contract。
4. Slice 2 composites。
5. inline layout batch 1。
6. 状态截图矩阵。
7. 剩余 inline style。
8. skill 制度化。

每步都要有独立验证。

### 7.3 编排者不采信“run done”

必须审计：

- 文件是否真的存在。
- 测试是否真的跑过。
- 证据目录是否生成。
- patch 是否能逆向校验。
- 输出是否与任务匹配。

`done` 只表示进程结束，不表示交付成立。

### 7.4 同一上下文的返修要缩小范围

实现 agent 保留上下文是优点，但返修时不要重发同一大 prompt。应：

- 说明上轮缺口。
- 明确“本轮只做什么”。
- 明确“不做什么”。
- 给独立验证命令。

## 8. 可复用清单

### UI 微观 design review

- 同区域控件高度是否一致。
- 同一行 input / select / button 是否同高。
- hover 是否引起布局位移。
- hover 是否使用突兀 underline。
- focus-visible 是否可见且不遮挡。
- disabled 是否语义明确。
- invalid 是否有字段级错误与汇总。
- loading / empty / error 是否都存在。
- toast 是否遮挡关键内容。
- dark mode 是否走 token。
- 375px 是否重组而不是压缩。
- coarse pointer 下触控目标是否达标。
- 是否绕过 primitive 写 inline magic style。
- 是否有可复现证据矩阵。

### skill 制度化检查

- 是否只写通用规则。
- 是否删除项目名 / 页面名 / 类名 / 固定像素。
- 是否区分 normal / benchmark。
- 是否进入 eval case。
- 是否同步 spec / ADR。
- 是否能通过静态门与隐私扫描。
- patch 是否能 `git apply --check` 与 reverse check。

### taskflow 收尾检查

- driver checkbox 是否只在子 change 全勾且 strict validate 后勾。
- 子 change 是否归档。
- proposal 验证记录是否回填。
- 证据路径是否写清。
- 是否未自动 commit / push。

## 9. 本轮成果快照

### 已落地

1. delivery-loop skill 创建并本机同步。
2. UI 质量闭环任务立项、设计、评审、冻结。
3. taskflow driver 与 4 个子 change 建立。
4. foundation 完成并归档：
   - CSS 三层分离。
   - Slice 1 primitives。
   - stylesheet manifest。
   - browser DOM contract。
   - 窄屏顶栏横向溢出修复。
   - coarse pointer 目标修复。
5. composites 完成并归档：
   - Slice 2 canonical CSS 迁移。
   - 第一批 inline layout 治理。
   - 40 张状态截图矩阵。
6. pages 代码层清理在中断前已达到：
   - inline style 从 25 降到 12。
   - 静态门 42/42 OK。
   - 全量 299/299 OK。

### 未完成

1. pages 子 change 的 OpenSpec 回填与归档尚未做。
2. skills institutionalization 子 change 尚未做：
   - task-wizard 增加 UI contract。
   - delivery-loop 增加 normal UI contract / evidence manifest 字段。
   - role-based-reviewer 合并微观 design 检查。
   - eval / static gate / spec 或 ADR 同步。
3. 最终 product/design/engineer 全链路复核尚未做。
4. 项目运行服务仍在临时环境；生产 checklist 未执行。

## 10. 当前恢复入口

如果继续本轮工作，从以下状态恢复：

1. 项目侧：
   - 代码层面已具备三层 CSS、DOM contract、状态截图工具、299/299 测试。
   - 先跑全量测试与状态证据工具，再回填 pages 子 change。
2. 仓库侧：
   - 任务设计在 `tasks/ongoing/ui-quality-institutionalization/`。
   - driver 是 `ui-quality-institutionalization-driver`。
   - 剩余子 change：`pages`、`skills`。
3. 注意：仓库索引中可能存在与本会话无关的 staged 改动；继续提交时必须按路径分组，不能带入无关变更。

## 11. 最重要的原则

1. **先建契约，再改实现。**
2. **先小切片，再全链路。**
3. **DOM / 静态测试负责发现，截图负责确认。**
4. **委派输出必须独立审计。**
5. **失败先归因，修复只治一类病。**
6. **normal 给上下文，benchmark 才隔离期望。**
7. **skill 只制度化通用经验，不记录项目特例。**
8. **没有把任务推进到“可复验证据”，就不算完成。**
9. **一致性验证全绿不等于设计正确。** 契约测试验证的是「实现符合约定」，验不到「约定本身怎么来的」。token 值、档位划分、密度基准这类设计决策必须有可追溯推导；否则测试越全，循环论证越牢固。
10. **「设计内 / not a bug」必须有门。** 驳回任何 finding 前先问「这个约定的推导在哪」；拿不出推导就按 acceptance gap 处理。用户对观感的连续两次追问，通常就是推导缺失的信号。（已制度化：delivery-loop Stage 8 驳回门 + bydesign eval case；role-based-reviewer design.md 61/62 条）
11. **经验沉淀的判据是「换项目还会不会犯」。** 修复交付仓后必须追问泛化性：会再犯 → 同时走 skill-upgrader 沉淀通用规则；只在单一项目成立的修复才允许停留在项目内。特例化修复的标志是：规则里出现了只有当前项目才认识的名词。
