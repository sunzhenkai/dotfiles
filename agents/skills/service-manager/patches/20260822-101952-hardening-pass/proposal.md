# 服务管理硬化综合修复

- target: agents/skills/service-manager
- patch: 20260822-101952-hardening-pass
- risk: high
- status: proposed

## Intent

一次性落地此前 review 中的缺陷修复，改变模型在 discover / start / stop / status / logs / 总结 / 维护通道上的行为：

- 日志与缓存按项目 `<ph>` 隔离；runs 区分原生 `pgid/pid` 与 compose `container`
- 明确项目根判定、身份匹配、运行状态优先级（含 `port_busy`）
- start 缺 name 默认询问；`.env` 先检查不擅自复制；`setsid` 进程组启动与就绪验证
- stop 优先杀进程组；禁止默认 `fuser -k`；compose 带 `compose_file`/cwd
- discover **合并多源**（含 Justfile/Taskfile/mise 等），不再因 Makefile 短路
- `.service-manager.md` 冲突：人工标注 / 经验证 / 成功校正边界写清
- 只读 phase 总结精简；访问方式优先 `127.0.0.1`
- 生产更新优先仓库 patches 审计流程，不与 skill-evolver 混用
- 同步重写/增补 `evals/cases.yaml`

**非目标**：不改 `.agents/` 镜像、不实现真实脚本二进制、不填充虚假 examples。

## Conflict check

- 与现有 phase 名称兼容；收紧 stop/start 默认行为（更安全，可能比旧文「直接全起 / fuser」更爱询问）。
- Evolution 节与本仓 `pwd-skill-manager` 对齐，避免双通道改生产稿。
- 单 patch 覆盖多主题：用户明确要求「所有一块修复」，故合并为一轮高风险审计包。

## Rationale

缺陷彼此耦合（日志路径、pgid、stop、evals）。用户要求一次性修复；用单一可审计 patch 保证原子应用与回滚，并靠 eval 覆盖新门禁。

## Files

- `agents/skills/service-manager/SKILL.md`：硬化后的完整行为契约
- `agents/skills/service-manager/evals/cases.yaml`：与正文对齐的确定性用例（含新增门禁）

## Validation

- `git apply --check --recount`
- 应用后 `git diff --check -- agents/skills/service-manager`
- frontmatter `name` == 目录名；无绝对家目录/凭据
- 抽查关键新规则字符串与 eval id 存在
