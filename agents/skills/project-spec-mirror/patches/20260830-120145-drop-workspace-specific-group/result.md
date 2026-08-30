# 结果

- status: applied
- applied_at: 2026-08-30 12:03 (UTC+8)

## 实际改动

| 文件 | 变化 |
|------|------|
| `SKILL.md` | build 第 7 步末尾：无条件的「grep 同 group 已镜像仓」改为条件式，并写明理由 |
| `evals/cases.yaml` | `complete-mode-notes-mandatory` 两条 must：路径判据改 `<spec_root>`，grep 那条改条件式 |

## 验证

- `git apply --check --recount`：首次因 hunk 缺上下文失败，补足前后各一行上下文后通过
- `git apply --recount`：通过
- `git diff --check`：无空白错误
- `python3 -m unittest discover`：50 tests OK
- `rg "同 group" SKILL.md references evals`：无命中；仅 `experience/`、`evolutions/`、历史 `patches/` 保留原始记录

## 偏差

`change.patch` 在校验阶段修订过一次（补上下文行），未修改任何生产文件即完成修正，符合协议。
