# 开发/测试服务：0.0.0.0 绑定与热更新优先

- target: agents/skills/service-manager
- patch: 20260822-131746-dev-bind-hot-reload
- risk: medium
- status: proposed

## Intent

改变 `service-manager` 在本地**开发/测试**原生服务上的默认启动行为：

1. **绑定**：start/restart 时监听 `0.0.0.0`（全网卡），不默认只绑 `127.0.0.1`；在可逆、常见的栈约定下用环境变量或官方 host 参数补绑定。
2. **热更新**：discover / 选 command 时优先 `dev`/`watch`/`--reload` 等热更新入口，而非生产向 `start`/`serve`。

触发：用户对该 skill 做 start/restart/discover，且目标为开发/测试向服务。

非目标：不强制改写人工标注或用户本会话指定的 command；不把 compose 依赖（db/redis 等）或纯生产入口改成热更新；不改 `.agents/` 镜像；不实现独立二进制。

## Conflict check

- 与现有「访问方式优先 `127.0.0.1`」不冲突：`0.0.0.0` 是监听地址，本机访问仍可写 `127.0.0.1`；可补充局域网入口说明。
- 与「人工标注优先 / 不瞎猜 command」一致：无法安全推断 host 补法时不擅自改命令，只提示并询问。
- 与「缺 name 默认询问」无冲突。
- 会改变 discover 在多候选时的默认选择（更偏 `dev`），属预期行为收紧。

## Rationale

本地开发常见需求是 LAN 可达与改代码即生效；当前 skill 只扫描 `dev` 脚本但未要求宽绑定，也未规定多候选时热更新优先。规则按常见栈给可执行补法，公开复用、可验证。

## Files

- `agents/skills/service-manager/SKILL.md`：新增「开发/测试启动约定」；discover/start/模板/总结对齐
- `agents/skills/service-manager/evals/cases.yaml`：新增热更新优先与 0.0.0.0 绑定用例

## Validation

- `git apply --check --recount`
- 应用后 `git diff --check -- agents/skills/service-manager`
- frontmatter `name` 与目录名一致；无个人隐私/绝对家目录
- 抽查关键规则字符串与新 eval id 存在
