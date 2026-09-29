# decision — 20260921-optional-skills-verify

**promote**（内容早已落地；本 decision.md 补记于 2026-09-29）

## 落地证据

`git log -S` 全历史命中：optional 条目规则于 `c0622a3`（2026-09-24 18:39，`skills-store: 收掉 jailbreak_role 对 MIT LICENSE 套话的误报，并重锁外部 skill`）
进入本仓生产稿 `.agents/skills/update-external-skills/SKILL.md`，晚于本 proposal 三天，且至今仍在。

对应正文位置：**坑 9**（`optional: true` / group 被注释 ⇒ 本机无副本属预期，只验上游 `tree_hash == content_hash`）
与 **坑 10**（本机恰有非托管陈旧副本时的四信号定性法）。

## 本目录为何只剩 proposal.yaml

提案被采纳时没人回来写候选稿与决议记录，因此这个目录看上去与"提案挂着没人管"完全同形。
判据只能是 git 历史，文本比对无效——本 skill 的 `evolutions/20260929-scripted-verify` 在同一天以另一种方式复现了同一个坑
（内容已随合并落地、状态仍写 `proposed`）。

## 后续

本 proposal 的机械化版本已由 `src/agents/lock_verify.py` 承担（`NOT-INSTALLED` 出口标签即坑 9 的自动判定），
经 `evolutions/20260929-scripted-verify` 于 2026-09-29 落地。手工规则仍保留在正文，作为脚本不可用时的兜底。
