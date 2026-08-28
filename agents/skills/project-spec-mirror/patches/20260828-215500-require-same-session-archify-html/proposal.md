# 识别出的图必须在本轮 deliver HTML

- target: agents/skills/project-spec-mirror
- patch: 20260828-215500-require-same-session-archify-html
- risk: medium
- status: proposed

## Intent

堵住「列出需要的图、写一句后续用 archify、把 INDEX 当待办」这条逃逸路径。触发：build / update / maintain 已经判定模块地图、调用链、状态机或数据流需要图。行为改为：archify CLI 可用时，本轮 Read 已安装的 Skill、写 JSON、`validate`、`deliver` HTML；会话 skill 列表没有 archify 不等于未安装。非目标：不把 archify schema/渲染器拷进本 Skill；不要求 concise 无关系可表时硬出图；不改 specctl 去生成 HTML。

## Conflict check

与「未安装时表格兜底、禁止假 HTML」不冲突：兜底仍在，但判定收窄为找不到 SKILL.md 或 `bin/archify.mjs`。与 pretty-view-html / html-diagram 不冲突：工程图仍只走 archify。不扩大 specctl 职责。

## Rationale

当前正文把出图写成可选委托，又允许「写明缺口」。执行时被理解成可以只写候选清单。eval 只禁止「未安装却声称已交付」，不禁止「已安装却写暂未生成」。这条规则跨项目成立，可用契约测试和 eval 条目验证。

## Files

- `SKILL.md` — build 第 6 步改为本轮交付，占位算未完成
- `references/diagrams.md` — 加载路径、deliver 命令、禁止待办 INDEX
- `references/layout.md` — overview / 展示原则只链已存在的 HTML
- `evals/cases.yaml` — 补 must / must_not
- `tests/test_skill_contract.py` — 锁关键措辞

## Validation

- 应用前：`git apply --check --recount`
- 应用后：`git diff --check`；`python3 -m unittest`（skill tests）；frontmatter 与引用路径；无私有信息
