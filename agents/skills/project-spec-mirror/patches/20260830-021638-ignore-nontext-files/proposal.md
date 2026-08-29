# 仅梳理未忽略的文本文件

- target: agents/skills/project-spec-mirror
- patch: 20260830-021638-ignore-nontext-files
- risk: medium
- status: proposed

## Intent

统一 inventory、diff、route 与 symbols 的源文件边界：

- 继续跳过 `node_modules`、vendor、构建产物、密钥和外来仓。
- 按 source 中的 `.gitignore` 规则跳过 ignored 路径；Git source 使用自身仓库规则，非 Git source 使用临时 bare Git 元数据解释 `.gitignore`，不修改 source。
- 即使文件已经被 Git 跟踪，只要当前 `.gitignore` 明确忽略，也不进入镜像。
- 仅保留文本文件：已知二进制扩展、含 NUL 或控制字符比例明显异常的内容跳过。
- 删除路径无法读取内容时，按扩展判断，避免把普通文本删除误丢掉。

## Conflict check

- 现有 `IGNORE_DIR_NAMES` 已覆盖 `node_modules`，保持不变。
- 现有 `list_git_files` 使用 `git ls-files`，只能排除未跟踪 ignored 文件；新增 `git check-ignore --no-index` 以满足显式 ignore 语义。
- 现有 `looks_binary` 只检查 NUL 且没有用于 inventory；升级为文本启发式并接入统一过滤。
- `.gitignore` 是规则文件自身，除非被更高层规则忽略，否则仍作为文本证据保留。
- 不修改用户仓库、不创建 source 内临时 `.git`，非 Git 匹配只使用系统临时目录。

## Rationale

规格镜像应关注可读、可解释的工程事实。忽略规则表达项目明确排除的内容，二进制资源无法直接梳理为 Markdown；在 inventory 和 diff 使用同一过滤逻辑可避免首次 build 与后续 update 范围漂移。

## Files

- `agents/skills/project-spec-mirror/SKILL.md` — 明确只处理未忽略文本文件。
- `agents/skills/project-spec-mirror/references/routing.md` — 更新统一过滤契约。
- `agents/skills/project-spec-mirror/scripts/specctl.py` — 实现 `.gitignore` 与文本内容过滤。
- `agents/skills/project-spec-mirror/evals/cases.yaml` — 增加 ignored/non-text 边界。
- `agents/skills/project-spec-mirror/tests/test_specctl.py` — 覆盖 Git、非 Git ignored 文件、跟踪后 ignored 文件和无扩展二进制。

## Validation

- `git apply --check --recount` 应通过。
- 生产文件 `git diff --check` 应通过。
- `python3 -m unittest discover -s agents/skills/project-spec-mirror/tests` 应通过。
- inventory、diff 与 route 对 ignored/non-text 文件应保持一致。
