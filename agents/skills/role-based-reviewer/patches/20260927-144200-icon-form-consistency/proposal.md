# design 角色补控件基线与 icon 形态检查

- target: agents/skills/role-based-reviewer
- mode: update
- patch: 20260927-144200-icon-form-consistency
- risk: medium
- status: proposed

## Intent

UI 评审在「视觉与一致性」之外缺一组可静态判定的机械规则：同表单控件被类型特例改高（如取色器、日期框单独定档）、表单收尾间距手写 magic number、功能性 icon 用裸字符或 emoji 码点充当。这类问题的共同根因是「没有契约」，逐个项目点样式治不住，应在 design 角色清单里制度化。

要改变的行为：design.md 新增「控件基线与 icon 形态」小节，全部措辞通用，不含任何项目名、类名、像素值或本机路径。

非目标：不改既有一至八节的判级与措辞；不新增运行态必查项（新运行态条目为 ⚪ 默认不报）；不改 role-vocabulary 与 preload 协议。

## Conflict check

- 第 5 节「视觉与一致性」已有 token 检查（32 条）；新小节与其互补不重复：32 条管「不新增硬编码值」，新条目管「同上下文同高」「间距来源」「icon 形态」三类结构性契约。
- 与 28 条（touch target）不冲突：一个管可点尺寸下限，一个管同高与形态。
- 通用性：规则只引用「同一表单上下文」「高度 token」「icon primitive」「emoji 码点」等可复用概念，可随 skill 开源分发。

## Rationale

三个反复出现的缺陷形态都有相同的机制解：契约先于实现。类型特例是同表单高度不一致的常见根因；magic number 间距让「按钮与上方字段太挤」这类评审意见无法被机械判定；裸字符 / emoji icon 的渲染依赖字体度量与彩色 emoji 字体，跨环境必坏。写成 `[代码]` 可判定条目后，diff 评审即可拦截，不必等运行态截图。

## Files

- `agents/skills/role-based-reviewer/references/roles/design.md` — 新增第 9 节（56–60 条）

## Validation

- 应用前：`git apply --check --recount agents/skills/role-based-reviewer/patches/20260927-144200-icon-form-consistency/change.patch`（仓库根执行）。
- 应用后：`git diff --check`；实际 diff 与 proposal 一致；无项目专有名词 / 本机路径 / 凭据。
- 本轮经 delivery-loop 目标明确授权「总结归纳到对应 skill」，按 medium 门禁视同已确认，应用后补 `result.md`。
