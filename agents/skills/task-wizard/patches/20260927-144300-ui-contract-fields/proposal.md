# 质量画像补 UI 交付的 design 底线字段

- target: agents/skills/task-wizard
- mode: update
- patch: 20260927-144300-ui-contract-fields
- risk: medium
- status: proposed

## Intent

质量画像的 design 底线只写「视觉方向、关键页面、必备状态」，对 UI 一致性类交付约束不住：控件密度上下文（哪些 surface 常规档、哪些密集档）、icon 形态契约（是否单一 primitive、是否禁裸字符/emoji）、表单间距来源、以及「哪些靠 DOM/静态断言、哪些必须截图确认」的证据分工。缺这些字段，实现者会把同表单高度不一、icon 字体依赖当成「风格选择」蒙混过审阅。

要改变的行为：quality-profile.md 新增「UI 交付的 design 底线必须回答」小节：凡画像覆盖含界面交付，design 底线除原有内容外必须能用一句话回答四个契约问题（密度分档、icon 形态、间距来源、证据分工），并给出判定为「不适用」的写法。措辞全部通用。

非目标：不改字段总表的五顶层结构；不改显式降级规则；不改缺字段判级逻辑（四个问题答不出仍按「空泛形容词」归 P0，复用现有判定）。

## Conflict check

- 与「每条底线写成可检查的话」一致：四个问题是「可检查」在 UI 一致性维度的具体化，不是新增评分维度。
- 与 role-based-reviewer design 角色新第 9 节互补：画像在交付前约束实现输入，reviewer 在交付后判定，两处措辞均为通用契约，不互相复制清单。
- 通用性：不出现项目名、类名、像素值；「取色器/日期框」等仅以示例身份出现。

## Rationale

UI 一致性缺陷的共同根因是契约缺失而非样式细节。把四个问题写进画像，task-wizard 完成门与 task-explore 快照天然携带它们，实现派发时无需额外提醒；reviewer 可逐条对照判定，避免「高质量」式形容词。

## Files

- `agents/skills/task-wizard/references/quality-profile.md` — 新增「UI 交付的 design 底线必须回答」小节

## Validation

- 应用前：`git apply --check --recount agents/skills/task-wizard/patches/20260927-144300-ui-contract-fields/change.patch`。
- 应用后：`git diff --check`；diff 与 proposal 一致；无项目专有名词 / 本机路径 / 凭据。
- 本轮经 delivery-loop 目标显式授权，medium 门禁视同已确认，应用后补 `result.md`。
