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
check 'taskflow spec' openspec/specs/taskflow-orchestration/spec.md '质量画像与降级进入 proposal' || fail=1
check 'reviewer ADR' docs/adr/0032-role-reviewer-accepts-structured-workflows.md '结构化工作流' || fail=1

printf '\nsummary: ' | tee -a "$out"
if (( fail == 0)); then echo 'PASS' | tee -a "$out"; else echo "FAIL($fail)" | tee -a "$out"; fi
exit "$fail"
