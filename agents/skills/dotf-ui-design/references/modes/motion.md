# Motion 模式

动画/动效/交互手感的专项审计与改进路线图。产出动效 findings + design-plans/ 计划；只读产品源码。

按 [../improve-animations/SKILL.md](../improve-animations/SKILL.md) 与其 [AUDIT.md](../improve-animations/AUDIT.md) 执行，骨架：

1. **Recon**：技术栈、动效库、token 约定、产品性格、频率地图（每天 100+ 次的高频元素 vs 偶发 vs 罕见）。
2. **审计八类**：目的与频率、缓动与时长、物理性与 origin、可中断性、性能、可访问性、一致性与 token、错失的机会。大仓库按类别并行只读子代理。
3. **Vet**：逐条回读 file:line 确认，绝不呈现没亲自确认过的 finding；按杠杆（影响÷成本）排序出表（HIGH/MEDIUM/LOW），另列 2–4 条 missed opportunities；停下等用户选择。
4. **计划**：用 [../improve-animations/PLAN-TEMPLATE.md](../improve-animations/PLAN-TEMPLATE.md)；数值一律照抄 AUDIT.md，绝不凭记忆近似；落盘、状态与承接见 [../plans.md](../plans.md)。

## Override（与 vendor 冲突时以本节为准）

| 项 | vendor | 本 skill |
| --- | --- | --- |
| 首次响应 | bare 调用时只回 "I'm ready to audit your animations…" | 入口已完成路由，直接开始 Recon，不输出该问候 |
| 计划目录 | `plans/`（或 `animation-plans/`） | `design-plans/`；另有用途时改 `ui-design-plans/` |
| `execute <plan>` | 支持派发 executor 子代理 | 不支持；执行统一走 plans.md 的承接协议 |
| 计划索引 | `plans/README.md` | `design-plans/README.md`，字段见 plans.md |
| 深度档位 | quick ≈5 条 HIGH | 保持 vendor：`quick`（只查高频组件，约 5 条，只留 HIGH）/ `standard`（默认）/ `deep`（含营销页，加 LOW 打磨项） |
| feel check 取证 | 计划内写明验证方式 | 执行 feel check 时按 [../visual-evidence.md](../visual-evidence.md) 采集慢放与 reduced-motion 对比 |

## 品味判断

动效数值与哲学以 AUDIT.md 为唯一来源，计划里的曲线、时长、spring 配置照抄不近似；产品性格（playful vs crisp）判断与 design 模式同源。
