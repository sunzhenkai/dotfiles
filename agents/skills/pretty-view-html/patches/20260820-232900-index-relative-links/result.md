# Result

- target: agents/skills/pretty-view-html
- patch: 20260820-232900-index-relative-links
- risk: medium
- status: applied
- applied-at: 2026-08-20T23:28:25+08:00

## Validation

- `git apply --check --recount`: pass
- `git diff --check`: pass
- target tests: not-available；已核对当前文件目录基准、自定义输出根、嵌套索引示例和完成检查
- privacy check: pass

## Notes

补丁按用户确认内容应用，无实际偏差。未执行 sync、commit 或 push。
