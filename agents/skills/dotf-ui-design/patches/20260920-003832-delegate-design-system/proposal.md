# 设计系统治理明确转交 ui-template-design

- target: agents/skills/dotf-ui-design
- mode: update
- patch: 20260920-003832-delegate-design-system
- risk: medium（工作流措辞变化；用户已明确批准）
- status: proposed

## Intent

把"设计系统沉淀"的转介从软措辞（"若环境中有设计系统治理类 skill 如 ui-template-design"）改为明确转交 ui-template-design（同编目默认安装的公开 skill）。三处：

1. 入口判断规则：需要新建或治理设计系统时，明确转交 ui-template-design。
2. modes/audit.md「设计系统缺位」：停止审计后，将设计系统沉淀明确转交 ui-template-design（创建 / 领养 / 迭代 design-system Active Instance），契约就位后恢复审计。
3. modes/design.md recon：需要新建或治理设计系统时转交 ui-template-design，不在本模式内造体系。

非目标：不改 ui-template-design 本身；不新增其他转介规则。

## Conflict check

ui-template-design 是同编目（agents/skills.yaml，ui-templates 组，非 optional）默认安装的公开第三方 skill，非项目级工具、非本仓库布局特例，点名不违反公开性约束。与"不另造组件体系"的既有边界方向一致，是把边界另一侧的承接方坐实。

## Rationale

默认编目保证两者同装，软降级措辞只会让用户在缺契约时得到模糊建议；明确转交使 audit 缺位路径有确定出口，且 design/audit 两处措辞一致。

## Files

- `agents/skills/dotf-ui-design/SKILL.md`
- `agents/skills/dotf-ui-design/references/modes/audit.md`
- `agents/skills/dotf-ui-design/references/modes/design.md`

## Validation

- 应用前：`git apply --check --recount`。
- 应用后：`git diff --check`；三处转交措辞一致且无"若环境中"残留；链接与 frontmatter 不变。
