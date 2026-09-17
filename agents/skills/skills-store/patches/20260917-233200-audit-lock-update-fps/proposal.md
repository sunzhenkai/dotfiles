# 收紧 lock-update 仍卡住的审计误报

- target: agents/skills/skills-store
- mode: update
- patch: 20260917-233200-audit-lock-update-fps
- risk: medium
- status: proposed

## Intent

把 lock-update 反复卡住的三类机械误报收掉，真阳性保留。

- `credential_paths`：`.env` 后的 `read` 命中 `README`。改为独立单词；并补 `cat`/`source` 在 `.env` 之前的写法。
- `eval_external`：单词 Eval + Markdown 反引号被当成 `eval \`curl\``。去掉裸反引号，只认 `eval $(…)` / curl / wget / `base64 -d`。
- `internal_url`：JSON Schema `$id` 的 `https://*.local/schemas/` 不是内网。`.local` 从 TLD 列表拿掉，保留 `.internal` / `.corp` / `.intranet` / `localhost`。
- `browser_session`：文档「不记录 cookie」走与 sudo 相同的反面例子跳过。

非目标：不改 npx 安装路径的警告确认；不删规则给单个 skill 放行。

## Conflict check

- 延续上一轮精度修复，不与「禁止安装当场改脚本」冲突。
- `cat ~/.ssh/id_rsa`、`eval $(curl …)`、`https://git.corp…`、`document.cookie` 仍应命中。

## Rationale

wizard / ui-template-author 被阻断后会停在旧 revision。同一 source 上只要有一条落后，lock-update 每次都把整组重拉、重审，所以不丝滑。这些命中不是特殊安全情况。

## Files

- `agents/skills/skills-store/scripts/audit-skill.sh`
- `agents/skills/skills-store/SKILL.md`

## Validation

- `git apply --check --recount`
- 夹具：wizard 的 `.env`+`README`、Eval+反引号、schema `.local` `$id` 不再阻断；`eval $(curl)`、`~/.ssh/id_rsa`、`.corp` URL、`document.cookie` 仍命中
