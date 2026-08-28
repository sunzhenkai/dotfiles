# Result

- target: agents/skills/project-spec-mirror
- patch: 20260828-211150-important-brief-redact-secrets
- risk: high
- status: applied
- applied-at: 2026-08-28T21:11:50+08:00

## Validation

- `git apply --check --recount`: pass
- `git diff --check`: pass
- target tests: `python3 -m unittest discover -s agents/skills/project-spec-mirror/tests` — 31 tests, OK
- privacy check: pass（生产正文无真实产品名、绝对家目录或密钥原文；`__pycache__` 字节码中的本机路径不计入）

## Notes

实际 diff 与 proposal 一致：`important` 由「可忽略」改为「简述 + 最低密度示例」；公共契约点名 `AppKey` / `SecretKey` 等字面量必须 `<REDACTED>`。示例使用虚构 `notify-client/`，未写入用户给出的真实包路径。未 commit / 未 sync。已有镜像若已抄过密钥，需要另开维护轮脱敏，本 patch 只改 Skill 规则。
