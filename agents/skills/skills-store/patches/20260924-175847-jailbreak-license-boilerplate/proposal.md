# 收紧审计：MIT LICENSE 套话不再命中 jailbreak_role

- target: agents/skills/skills-store
- mode: update
- patch: 20260924-175847-jailbreak-license-boilerplate
- risk: medium
- status: applied

## Intent

`jailbreak_role` 的 `without (any )?limit` 分支命中 MIT/BSD 授权正文的 `without limitation the rights`，
使锁内 skill 子目录只要带 `LICENSE` 就必然 `exit 2`。收掉这一处过宽 token，门禁语义不变：
阻断仍要逐条豁免，警告仍要确认。

- `without limit` / `without any limit(s)` 仍命中；只在后面接 `ation` 时放过。
- `no restrictions`、`you are now`、`act as`、`pretend to be`、`DAN mode`、`jailbreak` 分支不动。

非目标：不删规则、不为某个具体 skill 放行；不放开 `LICENSE` 文件的扫描范围
（`TEXT_NAMES` 保留 `LICENSE`，注入文本仍可被其余规则命中）。

## Conflict check

- 属于 SKILL.md 划定的「过宽 token 精度修复」，不是「为放行而放宽关键词」：修的是法务套话误报，
  真实越狱措辞覆盖不变。
- 与 `credential_paths` 已有的 lookahead 惯例一致（排除 `~/.ssh/config`、`~/.ssh/senv/`）。
- 已知误报表同步说明豁免范围，复核通道仍然要求逐条读原文。

## Rationale

archify lock 升级被 `LICENSE:8` 一条挡住（本次 `make skills-lock-update` 报 `blocked=1`）。
archify 是唯一把 `LICENSE` 放进锁内子目录的 source，所以只有它反复触发；
每次重锁都要人工豁免同样一句话，不可复用。

## Files

- `agents/skills/skills-store/scripts/audit-skill.sh`：`jailbreak_role` 加 `(?!ation)` 与说明注释
- `agents/skills/skills-store/SKILL.md`：已知误报表标注豁免范围
- `tests/test_audit_skill.py`：新增 MIT `LICENSE` 不误报 + 三条真实越狱措辞仍阻断
  （测试在仓库 `tests/`，不在本 skill 目录，未进 `change.patch`）

## Validation

- `python3 -m pytest -q tests/test_audit_skill.py tests/test_lock_update.py` → 全绿
- 对 upstream archify @ `9e35d2b0b39b` 跑 `audit-skill.sh`：`jailbreak_role` 不再命中，仅剩 `internal_url` WARN（exit 1，默认 fail-open 接受）
- `make skills-lock-update` → `blocked=0`，archify 前进

不拿「对 skills-store 自身目录跑审计」当验证：该 skill 的文档正文逐条列出它要检测的关键词，
自审必然大量命中（本轮前即有 26 项阻断），与本改动无关。
