#!/usr/bin/env bash
# 最近执行报告：读写 XDG state，脱敏 schema
# 版本: REPORT_SCHEMA_VERSION=1

REPORT_SCHEMA_VERSION=1

dotf_state_dir() {
  local base="${XDG_STATE_HOME:-$HOME/.local/state}"
  printf '%s\n' "${base}/dotf"
}

dotf_report_path() {
  printf '%s\n' "$(dotf_state_dir)/last-run.json"
}

# 用法: dotf_report_save <os> <profile> <result_lines...>
# result_lines 为 RESULT\t... 行
dotf_report_save() {
  local os_id="$1"
  local profile="$2"
  shift 2
  local dir path
  dir=$(dotf_state_dir)
  mkdir -p "$dir"
  chmod 700 "$dir" 2>/dev/null || true
  path=$(dotf_report_path)

  python3 - "$path" "$REPORT_SCHEMA_VERSION" "$os_id" "${profile:-}" "$@" <<'PY'
import json, sys, os
from datetime import datetime, timezone

path, ver, os_id, profile = sys.argv[1:5]
actions = []
for line in sys.argv[5:]:
    parts = line.split("\t")
    if len(parts) < 7 or parts[0] != "RESULT":
        continue
    # 脱敏：reason 截断，去掉疑似密钥片段
    reason = parts[6][:200]
    for token in ("KEY=", "TOKEN=", "SECRET=", "PASSWORD=", "Bearer "):
        if token.lower() in reason.lower():
            reason = "redacted"
            break
    actions.append({
        "status": parts[1],
        "module": parts[2],
        "action": parts[3],
        "duration_ms": int(parts[4] or 0),
        "exit_code": int(parts[5] or 0),
        "reason": reason,
    })

doc = {
    "version": int(ver),
    "saved_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    "os": os_id,
    "profile": profile or None,
    "actions": actions,
}
tmp = path + ".tmp"
with open(tmp, "w", encoding="utf-8") as f:
    json.dump(doc, f, ensure_ascii=False, indent=2)
    f.write("\n")
os.replace(tmp, path)
os.chmod(path, 0o600)
print(path)
PY
}

# 读取报告；失败打印原因到 stderr，返回非零
# 成功时把 JSON 打到 stdout
dotf_report_load() {
  local path
  path=$(dotf_report_path)
  if [ ! -f "$path" ]; then
    echo "错误: 无最近执行报告 ($path)" >&2
    return 1
  fi
  python3 - "$path" "$REPORT_SCHEMA_VERSION" <<'PY'
import json, sys
path, want = sys.argv[1], int(sys.argv[2])
with open(path, encoding="utf-8") as f:
    doc = json.load(f)
ver = doc.get("version")
if ver != want:
    print(f"错误: 报告版本不兼容 (got={ver}, want={want})", file=sys.stderr)
    sys.exit(2)
json.dump(doc, sys.stdout, ensure_ascii=False)
print()
PY
}
