# 增加详尽模式文件整理粒度

- target: agents/skills/project-spec-mirror
- patch: 20260828-190900-detailed-file-granularity
- risk: medium
- status: proposed

## Intent

详尽模式不再只有一种文件整理深度；开始 build 或从 concise 升级到 detailed 时，用户可选择：

1. `complete`：完整整理所有有业务含义的文件；
2. `important`：只整理重要文件，忽略或合并简单文件，但不得忽略有业务含义的文件；
3. `lightweight`：沿用当前轻量模式，只维护模块级文件表与已有知识页。

未指定时默认 `important`。`.mirror.json` 用 `detail_level` 保存选择；`mode` 仍表示 `concise|detailed`。

## Conflict check

现有文档只有 `concise|detailed`，且 detailed 默认不区分文件整理范围；现有 specctl 也未保存该选择。本 patch 扩展而不改变 `mode` 的含义，并保留旧镜像缺少 `detail_level` 时按 `important` 解释。

## Rationale

三档粒度覆盖完整性、可维护性和速度之间的常见取舍；把选择写入状态文件，可让后续 update 使用同一规则，避免每次重新猜测。重要文件模式明确排除“仅无业务含义”的文件，防止以简化为由遗漏业务证据。

## Files

- `agents/skills/project-spec-mirror/SKILL.md` — 声明详尽模式先选择文件整理粒度，并同步 build/set-sync 规则。
- `agents/skills/project-spec-mirror/references/modes.md` — 定义三档粒度、默认值和各档文件处理规则。
- `agents/skills/project-spec-mirror/scripts/specctl.py` — init/set-sync/validate 保存并校验 `detail_level`。
- `agents/skills/project-spec-mirror/evals/cases.yaml` — 增加三档选择及默认值验收。
- `agents/skills/project-spec-mirror/tests/test_specctl.py` — 验证 init 默认并保存重要文件模式。

## Validation

- `git apply --check --recount` 应通过。
- `git diff --check -- agents/skills/project-spec-mirror` 应通过。
- `python3 -m unittest discover -s agents/skills/project-spec-mirror/tests` 应通过。
