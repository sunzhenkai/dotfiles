# 收紧审计：ACP session 与 shebang 脚本误报

- target: agents/skills/skills-store
- mode: update
- patch: 20260917-232453-audit-precision
- risk: medium
- status: proposed

## Intent

把 `audit-skill.sh` 的两类机械误报收掉，安装门禁语义不变：警告仍要确认，阻断仍要逐条豁免。

- `browser_session` 的 `session` 过宽，命中 ACP `session/new` 等协议名。改为 `sessionStorage`，仍抓 `cookie` / `localStorage` / `browser-profile` / playwright storage。
- `binary_in_skill`：GNU `find -regex` 默认 emacs 语法，TEXT_EXTS 排除无效；`file` 又把 shebang 纯文本标成 executable。改用与文本扫描相同的 bash `=~` 排除，且只认 ELF / Mach-O / PE32 / shared object。

非目标：不删规则、不放宽关键词来给某个 skill 放行；不改 npx 安装路径「警告必须用户确认」。

## Conflict check

- 与「禁止为放行而改关键词表」不冲突：本轮是精度修复，安装当场仍不得改脚本。
- `never-edit-audit-keywords` 收成「禁止删规则/放宽关键词、禁止安装当场改脚本」，允许走本 Skill 更新做精度修复。
- 前端 `localStorage` / `cookie` 仍 WARN，已知误报表保留。

## Rationale

agent-roster lock 升级被 4 条 ACP `session/` 与 1 条 Python shebang 挡住。二者都是检测过宽，不是风险。修检测比每次 `ACCEPT_WARN` 更可复用。

## Files

- `agents/skills/skills-store/scripts/audit-skill.sh`：收紧 `browser_session`；修正二进制扫描
- `agents/skills/skills-store/SKILL.md`：更新已知误报与「禁止为放行改表」的边界
- `agents/skills/skills-store/evals/cases.yaml`：对齐上述边界

## Validation

- 应用前：`git apply --check --recount` 本目录 `change.patch`
- 应用后：`git diff --check -- agents/skills/skills-store`；对 ACP `session/` markdown 与 shebang `.py` 跑 `audit-skill.sh` 应 exit 0；`localStorage` 与 ELF 样例仍 WARN
