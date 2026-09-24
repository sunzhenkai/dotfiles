# Eval — 20260925-diff-outcome-branches

对照对象：2026-09-25 一轮真实重锁+验证的 `diff -r` 实际输出（两条目：一非 optional、一 optional）。
本 skill 无自带测试脚本，按指令级对照验证。

## 回归

按现行成功路径（非 optional 条目、内容有变）重放：其 `diff -r` 输出为
「Only in 上游: evals/evolutions/experience/patches」×4 + 「Only in 安装副本: __pycache__」+
kiro 末尾 `$ARGUMENTS`。
- 旧规则：前两类预期、`__pycache__` 落进「其余任何差异 → 回查 defaults」，需现场推断。
- 新规则：三条分支各自命中（1 / 3 / 2），结论均为预期，流程照常收口。
成功路径未被新规则打断。**无回归。**

## 模式

原先现场推断的两类情形，按新指令是否可机械执行：
- optional 条目三个 layout 全部 `No such file or directory`：新分支直接命中「查编目 →
  optional → 只验 tree_hash」，与本轮实际处置一致（tree_hash 已确认相符）。**可避免。**
- `__pycache__` 被字面规则误伤：新分支 3 明示「忽略即可」。**可避免。**

## 契约

无测试可跑；指令级对照如上。未引入新命令、新文件路径依赖仅 `agents/skills.yaml`
（原 step 4 验证 tree_hash 时本就要读 lock/编目）。

## 副作用

- 触发范围：未变（仍是显式点名 + content_hash 有变才进 step 4）。
- 判读方向：分支 3 把「本机侧多出运行残留」从「回查 defaults」改判为「忽略」，属预期的
  精度修正；其余任何差异仍回查 defaults，兜底句保留，未放松。
- 权限 / 破坏性操作 / 密钥：无涉及。

## 结论

**pass** — 回归、模式、契约、副作用四项均过。
