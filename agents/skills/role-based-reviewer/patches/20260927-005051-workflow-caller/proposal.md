# 门 1 承认「结构化调用的上游工作流」为正当调用方

- target: agents/skills/role-based-reviewer
- mode: update
- patch: 20260927-005051-workflow-caller
- risk: high
- status: proposed

## Intent

分阶段编排类工作流在「方案评审」环节固定委托本 skill（典型形态：复杂档计划评审以 `mode=review` + `roles=product,design,engineer` 结构化调用，并随附完成判据、质量画像 / 角色底线、显式降级清单、本环节审与不审的范围）。这类调用方既没有用户当轮点名，也不属于「用户写出 `roles=`」，按现有门 1 字面读来进不来；而门 2 与「视角推断」又写着「将超过 2 个角色先问用户」，固定三角色会被当成待确认的推断结果。

本 patch 改变的模型行为：

1. 门 1 增加第 4 条触发——工作流以结构化参数调用，且 `mode=review`、完整合法 `roles=`、审阅边界输入三者齐备时，承认为正当调用方。
2. 明确这不是自动入口：只说「现在进入评审环节」而没有结构化 `roles=` 与边界输入，仍不加载，按常规审查处理。
3. 明确「已指定 vs 推断」的界线：调用方传入完整 `roles=` 属已指定，用户当轮点名优先于传入值，两者都不增删；固定角色集即使超过 2 个也照单执行，不列候选、不反问。「将超过 2 个角色停下来问」限定为只对推断结果生效。
4. 输入段新增「审阅边界输入」条目与一条通用工作流调用示例；缺项时只按已有判据审查并在报告开头写明缺口，不扩大到「不审」列内容。

非目标：不改门 3 的发现克制与严重级别定义；不新增角色；不改 description（自动加载门禁的入口文本）；不改 references/ 下任何文件；不引入专有项目、具体 skill 名或仓库内工作流术语——正文只用「上游编排型工作流」这一通用措辞。

## Conflict check

- **门 1 原有三条触发**：全部保留，只追加第 4 条与一行「不算触发」补充，普通「看看代码 / 帮我 review」的反例照旧生效，门禁只收紧不放松。
- **门 2「一次推断将超过 2 个角色时先列出候选问用户」**：措辞本就限定在「推断」，但读者会把固定三角色误读为堆视角。patch 在门 2 补一行区分「已指定」与「推断」，并把「视角推断」段的「将超过 2 个角色」改写为「推断结果将超过 2 个角色」，两处收敛到同一判据，无残留矛盾。
- **「视角推断」首行「用户显式指定的 `roles` 优先，不再增删」**：扩展为「调用方传入的固定 `roles` 等同显式指定」，方向一致，不改变「用户优先」。
- **frontmatter description**：有意不改。其中「指定 roles=」已覆盖结构化调用形态，而 description 正是宿主决定是否加载本 skill 的文本，改动会直接冲击「普通 review 不自动加载」这条门禁，属超范围。
- **references/constraints.md「`roles` 可指定 1 个或多个；未指定时默认 engineer」**：与本 skill「已指定」分支一致，无需同步修改。
- **门 3 与调用侧的分级映射**（调用方把 Minor / Suggestion 映射为自有低级别）：门 3 默认只报 Blocker / Major 的行为不变，映射由调用方侧完成，不冲突。
- **历史 patch**：`20260828-183715-drop-task-workflow-downstream` 移除的是本 skill **下游**的任务工作流耦合（本 skill 不主动编排执行类流程）；本 patch 处理的是**上游**调用方的准入，方向相反且不复现该耦合——正文不点名任何具体 skill，也不承诺替调用方推进任务。
- **evals**：目标 skill 目录下不存在 `evals/`（无 `cases.yaml`），本轮不自建目录、不发明 eval 格式，按 patch 协议属 `self-upgrade` 范围，不夹带进 `update`。

## Rationale

改动可执行、可验证：门 1 第 4 条给出三项可核对的输入（`mode=review`、完整合法 `roles=`、边界输入），缺一即不触发；门 2 与推断段的界线让「固定角色集不反问」成为确定行为，而非常规审查里那样需要追问。同时保留原反例，使「普通帮我 review 不进入」与「结构化调用按三角色执行」两条可在同一份文本上分别判定，不互相覆盖。措辞保持通用，可随 skill 分发到任意 agent 环境。

## Files

- `agents/skills/role-based-reviewer/SKILL.md`
  - 门 1：新增工作流调用触发条 + 「不算触发」补充行
  - 门 2：新增「已指定 vs 推断」界线（超过 2 个角色不反问）
  - 输入：新增 `审阅边界输入` 条目；示例新增一条通用工作流调用形态
  - 视角推断：首行声明传入 `roles` 等同显式指定；「将超过 2 个角色」限定为推断结果

## Validation

- 应用前：仓库根执行 `git apply --check --recount agents/skills/role-based-reviewer/patches/20260927-005051-workflow-caller/change.patch`
- 应用后：
  - `git diff --check -- agents/skills/role-based-reviewer`；实际 diff 与本 proposal / `change.patch` 逐处一致
  - frontmatter 合法且 `name` 仍为 `role-based-reviewer`；description 与 patch 前逐字节相同
  - 门 1 为 4 条触发且保留原「不算触发」反例；门 2 / 视角推断两处对「超过 2 个角色」的表述不再互斥
  - 全文无专有项目名、绝对路径、凭据；未点名任何兄弟 skill
  - `make validate`（registry 校验）通过；引用链接 `references/*.md` 全部仍存在
- 未做（受本次任务边界限制）：本轮只产出 patch 与提案，不执行 `git apply`，因此无 `result.md`
