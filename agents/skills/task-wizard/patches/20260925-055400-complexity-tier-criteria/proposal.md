# 按低中高重写复杂度档位依据

- target: agents/skills/task-wizard
- mode: update
- patch: 20260925-055400-complexity-tier-criteria
- risk: medium
- status: proposed

## Intent

复杂度档位仍只取简单、中等、复杂，对应低、中、高。完成程度的高、中、低不参与选档。典型情况改为：简单通常是局部修改；中等通常是一个中等需求，可以跨多个模块或仓库，改动量稍大或逻辑稍微复杂；复杂是项目级重构、逻辑重塑，或业务逻辑复杂且涉及面广。先看复杂，命中任一条即复杂。单仓、顺序执行、没有并行不是降档理由。跨模块或跨仓本身停在中等。拿不准只发生在简单与中等之间。

触发：任务方案写建议路由时，以及 Goal 方案进入「写完之后」选档时。非目标：不改三档衔接（简单仍是 grill 后直接实现，中等仍是 OpenSpec，复杂仍是 task-explore → taskflow）；不把档位改名为低、中、高；不改审阅的完成程度。

## Conflict check

与完成程度的高、中、低冲突：两套都曾被叫成「高」。本轮在术语里把复杂度档位和完成程度拆开，档位名保持简单、中等、复杂。与旧信号冲突：跨仓跨模块、并行不再是复杂的必要条件；「拿不准往简单靠一档」不再适用于已命中复杂的方案。`openspec/specs/task-wizard-goal/spec.md` 里「交接后发现要拆多段再升复杂」不在本 patch 路径内，应用后另改一句，与新的复杂典型情况对齐。

## Rationale

旧的复杂信号是并列清单，执行者把「没有跨仓、没有并行」当成否决项，再用降档句把项目级方案降成中等。新依据按任务规模区分：局部修改、一个中等需求、项目级或涉及面广的逻辑。跨模块只说明可以是中等。

## Files

- agents/skills/task-wizard/SKILL.md — 复杂度路由表、降档规则、Goal「写完之后」的档位括号、外部参照后的重判句、交接后升档条件
- agents/skills/task-wizard/CONTEXT.md — 复杂度档位；完成程度不用于选档
- agents/skills/task-wizard/references/external-precedent.md — 重判不得把已命中复杂的档位降下来

## Validation

- 应用前：`git apply --check --recount`
- 应用后：`git diff --check`；frontmatter `name` 仍为 `task-wizard`；简单/中等/复杂的衔接句仍在；正文含「局部修改」「一个中等需求」「项目级重构」；「拿不准」不再把已命中复杂的方案降档；无本 skill 测试
