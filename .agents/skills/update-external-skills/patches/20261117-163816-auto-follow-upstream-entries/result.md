# Result

- target: .agents/skills/update-external-skills
- mode: update
- patch: 20261117-163816-auto-follow-upstream-entries
- risk: medium
- status: applied
- applied-at: 2026-11-17T16:45:00+08:00

## Validation

- `git apply --check --recount`: pass
- `git diff --check -- .agents/skills/update-external-skills`: pass
- frontmatter: 单行双引号 description，`name` 未变，与改前同构；已目视确认
- repo tooling（同轮代码侧）: `python3 -m pytest tests/ -q` → 743 passed；`make registry validate` 通过
- privacy check: pass（无内网地址、无凭据）
- mode check: pass（update 模式，只改正文；未 sync、未提交、未推送）

## Notes

正文从「只刷新已有 revision」改为「重锁自动增删父目录内条目 + 三个手工缺口」。坑 12 中原先记录的旧实现（硬失败 + 手写种子条目）保留为「工具出问题时才用」的备选，删除其独占的「种子 revision 已等于 HEAD」长段落——该场景在自动发现下不再出现。新增坑 17（`optional: true` 是默认也是天花板、发现范围收窄的理由）与坑 18（新条目同样过审计、失败计入 `blocked`）。
