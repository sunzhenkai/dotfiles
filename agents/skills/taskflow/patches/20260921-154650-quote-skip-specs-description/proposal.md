# 修复 cases.yaml 既有非法 YAML：给含冒号的 description 加引号

- target: agents/skills/taskflow
- mode: update
- patch: 20260921-154650-quote-skip-specs-description
- risk: low
- status: proposed

## Intent

`evals/cases.yaml` 第 30 行 `description: driver 必须显式 skip_specs: true` 的 value 含裸 `: `，`yaml.safe_load` 报 "mapping values are not allowed here"（HEAD 已存在，非上一轮 patch 引入）。给该值加双引号，使整份 evals 恢复可机器加载。不改变任何 case 语义。

非目标：不重写其它 description、不调整 case 内容。

## Conflict check

- none。仅引用风格修复，与 SKILL.md 及并行 patch `20260921-154244-optional-task-branch` 无重叠行。

## Rationale

evals 的前提是文件可被确定性加载；当前非法 YAML 使所有 case 无法运行。单行加引号即可修复，可验证（`yaml.safe_load` 通过）。

## Files

- `agents/skills/taskflow/evals/cases.yaml`：第 30 行 description 加双引号

## Validation

- 应用前：`git apply --check --recount` 本目录 `change.patch`
- 应用后：`git diff --check -- agents/skills/taskflow`；`python3 -c "import yaml; yaml.safe_load(...)"` 通过
