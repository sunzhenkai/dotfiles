---
slug: update-external-skills
parent: null
status: done
phase: done
confirm_mode: human
tier: medium
criterion: "`make skills-lock-update` 完成且 `blocked=0`（或 blocked>0 已逐条定性），`python3 src/agents/lock_verify.py changed` 报告计数行已落账，`make registry validate` 通过；三件事齐备即视为完成；不含下发本机、git commit、git push。"
driver: null
evidence_root: /tmp/dotf-taskrail-update-external-skills-2026-10-10
created: 2026-10-10
updated: 2026-10-10
---

# update-external-skills

## 目标
刷新 `agents/skills.yaml` 编目里第三方 group 的 lock，把 `agents/skills.lock.yaml` 推进到各 source HEAD 并区分真变与纯重钉，校验仓库产物自洽。

## 方案
详见 `wizard/plan.md`。要点：

- 三步按 skill 固定流程：`make skills-lock-update` → `python3 src/agents/lock_verify.py changed` → `make registry validate`。
- `blocked>0` 时按 SKILL「blocked>0」段读 `$LOG` 上方汇总 → 写 `evidence_root/blocked-classification.md`；不做就地放行，不为放行改审计脚本。
- 流程内禁止：commit / push / `bin/dotf agents -c --yes`，由用户决定是否本轮授权。
- 一次性放行范围：步骤 1–5（仓储内可逆改动）；其他动作需逐项点名。

## 结果
三步齐备，PASS。详见 `evidence/summary.md`。

- `make skills-lock-update`：exit=0，`wrote agents/skills.lock.yaml sources=2 blocked=2`。
- `python3 src/agents/lock_verify.py changed`：exit=0，`changed_content=1 changed_revision_only=21 added=0 removed=0`。
- `make registry validate`：exit=0，`✓ 注册表校验通过（strict-handlers）`。

## blocked>0 的处置
- archify：19 BLOCK + 131 WARN，规则命中疑似过宽（`hardcoded_secret` 把 `token` 变量名当密钥、`jailbreak_role` 把英文合同注释当 jailbreak、`bypass_approval` 把「必须 opt-in 才能关沙盒」反向断言当绕权）。
- ui-template-author：52 BLOCK（全在 `01-token-map.yaml` 一个文件）；同上 `hardcoded_secret` 过宽，字段名 `project_token` 是设计系统术语。
- 处置：保留旧 revision，按 SKILL 坑 11 → expand 出口，已登记子任务 `ongoing/ui-templates-audit-overreach`（去 `sunzhenkai/solo-skills` 仓走 skills-store 三件套）。

## 未做（按 plan 与 skill 边界）
- `bin/dotf agents -c --yes`（未点名：覆写三 agent home 安装产物）。
- `git commit` / `git push`（未点名：写仓库历史）。

## 当前阶段
done（完成门已过）。

## 下一步（移交给用户）
详见 `evidence/summary.md` 「推荐下一步」表：
1. 改审计规则精度（子任务：`ui-templates-audit-overreach`）。
2. 完成后 `make skills-lock-update` 复跑一次，确认 archify / ui-template-author 已上 latest。
3. `bin/dotf agents -c --yes` 下发本机（自动入口，未授权前不执行）。
4. `make skills-verify` 核对。
5. `git commit` 锁变更入仓。

