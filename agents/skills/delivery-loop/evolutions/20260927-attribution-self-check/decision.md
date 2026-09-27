# Decision

decision: promote
date: 2026-09-27

## 理由

1. 用户已确认 Evolution Proposal（2026-09-27）
2. 用户已确认候选 diff 与「契约项未覆盖是否接受」（2026-09-27）
3. eval.md 结论为 `pass`：回归 8 项全绿、原失败路径 4 环节全覆盖、副作用可控（未改触发条件 / 权限 / 硬边界）、过拟合扫描零命中
4. 生产改动与 proposal 声明一致，无夹带无关编辑

## 晋升内容

- `agents/skills/delivery-loop/references/loop-protocol.md`：Stage 8 段尾追加「归因自检」3 条规则
- `agents/skills/delivery-loop/SKILL.md`：第 10 步追加指向该自检的锚点引用

## 未覆盖项（如实记录，非失败）

契约项：三条规则是流程强制步骤，判定对象为「编排者是否执行自检」，无法构造 deterministic eval case；强行补会退化为文案自证。已接受此缺口。

## 候选正文的去向

promote 后已删除本目录下的候选正文副本（`SKILL.md` / `loop-protocol.md`）。理由：正文已进生产稿，
留住逐字副本会形成第二份真相源，改生产稿不会同步它，下一轮进化可能拿陈旧副本当底稿。

变更内容以 `proposal.yaml`（改什么）与本节（落到哪）为准，diff 可由 git 追溯。

## 后续

- 生产稿已覆盖，本仓库为 skill 源仓库。
- 需下发本机时由用户执行 `dotf agents -c`（本流程不擅自 sync / commit）。
