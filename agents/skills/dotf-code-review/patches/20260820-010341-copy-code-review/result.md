# Result

- target: agents/skills/code-review
- patch: 20260820-010341-copy-code-review
- risk: high
- status: applied
- applied-at: 2026-08-20T01:03:41+08:00

## Validation

- `git apply --check --recount`: pass
- `git diff --check`: pass
- target tests: `python3 -m unittest discover -s agents/skills/code-review/tests -v` — 5 tests passed
- privacy check: pass；仅保留测试用的 `test@example.invalid` 占位地址和 `.invalid` 示例域名
- source comparison: pass；3 个文件与 `~/dotf-code-review` 对应文件一致
- frontmatter/references: pass；`name: code-review` 与目录名一致，脚本和测试路径存在

## Notes

none
