#!/usr/bin/env bash
set -euo pipefail

root="${1:-$PWD}"
out="${2:-/tmp/agent-delivery-quality/regression/static-gates.txt}"
mkdir -p "$(dirname "$out")"
: > "$out"

check() {
  local label=$1 path=$2 pattern=$3
  printf '%-34s ' "$label" | tee -a "$out"
  if rg -q "$pattern" "$root/$path" 2>/dev/null; then
    echo 'PASS' | tee -a "$out"
  else
    echo "FAIL: $path !~ /$pattern/" | tee -a "$out"
    return 1
  fi
}

check_cmd() {
  local label=$1 command=$2
  printf '%-34s ' "$label" | tee -a "$out"
  if (cd "$root" && eval "$command") >/dev/null 2>&1; then
    echo 'PASS' | tee -a "$out"
  else
    echo "FAIL: $command" | tee -a "$out"
    return 1
  fi
}

fail=0
check 'wizard quality profile' agents/skills/task-wizard/SKILL.md '质量画像（复杂档必填）' || fail=1
check 'wizard profile reference' agents/skills/task-wizard/references/quality-profile.md '受众与场景|显式降级' || fail=1
check 'wizard hard trigger' agents/skills/task-wizard/SKILL.md '多个主页面|角色/权限边界|持久化数据' || fail=1
check 'wizard role gate' agents/skills/task-wizard/SKILL.md 'roles=product,design,engineer' || fail=1
check 'wizard pending gate' agents/skills/task-wizard/SKILL.md '降级未确认' || fail=1
check 'explore snapshot' agents/skills/task-explore/references/task-template.md '质量画像|显式降级' || fail=1
check 'explore decide gate' agents/skills/task-explore/references/phase-decide.md '不得冻结|降级未确认' || fail=1
check 'explore handoff gate' agents/skills/task-explore/references/phase-handoff.md '降级未确认|原文快照' || fail=1
check 'taskflow proposal snapshot' agents/skills/taskflow/SKILL.md 'Why` 逐字保留|逐字保留' || fail=1
check 'taskflow acceptance' agents/skills/taskflow/SKILL.md 'pending` 降级数为 0|pending 降级数为 0' || fail=1
check 'reviewer workflow gate' agents/skills/role-based-reviewer/SKILL.md '上游编排型工作流' || fail=1
check 'wizard spec' openspec/specs/task-wizard-goal/spec.md '复杂档质量画像门' || fail=1
check 'explore spec' openspec/specs/task-explore-lifecycle/spec.md '质量画像与降级快照' || fail=1
check 'taskflow delivery loop' agents/skills/taskflow/references/delivery-quality-loop.md 'skill gap|implementation bug|acceptance gap' || fail=1
check 'taskflow narrow-first' agents/skills/taskflow/references/delivery-quality-loop.md '窄切片先行|全链路.*只跑一次|只重跑受影响切片' || fail=1
check 'taskflow rubric dimensions' agents/skills/taskflow/references/acceptance-rubric.md '功能闭环|UI/UX|工程质量|画像一致性|证据' || fail=1
check 'taskflow rubric six UX' agents/skills/taskflow/references/acceptance-rubric.md '信息架构|视觉层级|关键状态|反馈|无障碍|响应式' || fail=1
check 'taskflow rubric threshold' agents/skills/taskflow/references/acceptance-rubric.md '五维均 ≥2|UI/UX 均值 ≥2.5' || fail=1
check 'taskflow normal input' agents/skills/taskflow/references/implementer-isolation.md '正常交付|保留语义的子范围|相关验收要求' || fail=1
check 'taskflow blind input' agents/skills/taskflow/references/implementer-isolation.md '盲测 / 基准复跑|benchmark / regression|不追加事后提示' || fail=1
check 'taskflow no default blind' agents/skills/taskflow/SKILL.md '普通任务不得盲派' || fail=1
check 'taskflow loop eval' agents/skills/taskflow/evals/cases.yaml 'delivery-quality-loop-three-way-triage' || fail=1
check 'taskflow rubric eval' agents/skills/taskflow/evals/cases.yaml 'acceptance-rubric-thresholds|rubric-not-second-ledger' || fail=1
check 'taskflow input evals' agents/skills/taskflow/evals/cases.yaml 'normal-delivery-input-context|blind-regression-input-isolation' || fail=1
check 'taskflow spec quality loop' openspec/specs/taskflow-orchestration/spec.md '交付质量闭环与验收 rubric' || fail=1
check 'taskflow spec input modes' openspec/specs/taskflow-orchestration/spec.md '普通复杂交付派发实现者时 MUST 提供|benchmark / regression' || fail=1
check 'reviewer description gate' agents/skills/role-based-reviewer/SKILL.md '上游工作流以 mode=review \+ 完整 roles \+ 审阅边界结构化调用' || fail=1
check 'reviewer ADR' docs/adr/0032-role-reviewer-accepts-structured-workflows.md '结构化工作流' || fail=1
check_cmd 'taskflow yaml parse' "python3 -c \"import yaml; yaml.safe_load(open('agents/skills/taskflow/evals/cases.yaml'))\""
check_cmd 'taskflow bundle reverse' "git apply --check --recount --reverse agents/skills/taskflow/patches/20260927-093845-isolation-modes/bundle.patch"
check_cmd 'taskflow patch reverse' "git apply --check --recount --reverse agents/skills/taskflow/patches/20260927-093845-isolation-modes/change.patch"
check_cmd 'reviewer patch reverse' "git apply --check --recount --reverse agents/skills/role-based-reviewer/patches/20260927-094200-structured-workflow-description/change.patch"

printf '\nsummary: ' | tee -a "$out"
if (( fail == 0)); then echo 'PASS' | tee -a "$out"; else echo "FAIL($fail)" | tee -a "$out"; fi
exit "$fail"
