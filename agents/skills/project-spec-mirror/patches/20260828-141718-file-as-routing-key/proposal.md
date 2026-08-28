# 文件改为路由键，取消每文件一页

- target: agents/skills/project-spec-mirror
- mode: update
- patch: 20260828-141718-file-as-routing-key
- risk: high
- status: proposed

## Intent

重定义人读叶子与详尽语义：阅读单位是模块；源文件只做清单行、同步路由键和证据路径。取消「详尽 = 范围内每个代码文件一页」及路径 `/` → `__` 拍平。详尽改为加深已有金字塔/切面页。`notes/` 仅为 opt-in 热点。update 按 `diff` 把变更文件映射到模块页（本轮文档规定算法；`specctl route` 留待下一轮）。

非目标：不改放置规则、确认门、git 默认分支、manual 块、密钥脱敏、OpenSpec 边界、archify、specctl 命令实现；不删除遗留 `files/`；不加 `--per-file-pages`。

## Conflict check

与现行 `modes.md` / `layout.md`「详尽为每个代码文件建 `files/` 页」直接冲突，本 patch 替换该约定。与切面/金字塔并存不冲突：切片仍是垂直切口，不是文件。`evals` 的 `detailed-over-80-asks` 随旧门禁删除并改写。不改 specctl，故命令表与 `COMMANDS` 仍一致。

## Rationale

git 的变更单位是文件，规格的阅读单位是领域金字塔。把二者绑成「一文件一页」会造成重复、rename 孤儿和不可维护的规模。文档先改契约，Agent 即可按 `routing.md` 手算映射；机械 `route` 命令下一轮再补，本轮仍可验证（unittest 不依赖新 CLI）。

## Files

- `agents/skills/project-spec-mirror/SKILL.md` — build/update/maintain、非目标、先读 routing
- `agents/skills/project-spec-mirror/references/layout.md` — 目录、模块页、`.mirror.json` 字段
- `agents/skills/project-spec-mirror/references/modes.md` — 简约/详尽与热点
- `agents/skills/project-spec-mirror/references/routing.md` — 新建：diff → 页
- `agents/skills/project-spec-mirror/references/knowledge.md` — 经路由更新知识页
- `agents/skills/project-spec-mirror/references/facets.md` — 切片 ≠ 文件
- `agents/skills/project-spec-mirror/evals/cases.yaml` — 替换 80 文件门禁，补新 case
- `agents/skills/project-spec-mirror/evals/README.md` — 一句说明详尽语义
- `agents/skills/project-spec-mirror/tests/test_skill_contract.py` — 要求 routing.md 存在

## Validation

- 应用前：`git apply --check --recount` 本 patch
- 应用后：`git diff --check -- agents/skills/project-spec-mirror`；`python3 -m unittest discover -s agents/skills/project-spec-mirror/tests`；frontmatter；references 存在；无私有信息
