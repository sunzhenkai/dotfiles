# Antigravity skills 桥接归入 `dotf agents -c`，模块名支持别名

`~/.gemini/config/skills.json` 把 `~/.agents/skills` 挂进 Antigravity 的全局 skill 发现路径。它管的是 agents 域（同一棵树、同一个诊断在 `src/agents/doctor.py` 的 `skills` 段），部署却挂在 `antigravity` 模块的 config 声明下。结果新机器按文档只跑 `dotf agents -c` 时漏掉桥接，doctor 一直 warn「运行 dotf antigravity -c」。

## 决定

1. **桥接成为 agents sync 的一个阶段。** `scripts/modules/agents/sync.sh` 在 instructions 之后新增 `bridge` 阶段，调用 `src/agents/antigravity_bridge.py`。该阶段不复制配置逻辑：它从 `modules.yaml` 读出 `antigravity.config` 声明，交给 `dotf_core.config_deploy` 的 `compile_config_plan` / `deploy_config`，所以策略、权限、备份、takeover 全部沿用既有实现。
2. **检测到 Antigravity 才写入。** 判断依据是 `~/.gemini/antigravity/` 存在、或桥接文件已存在（含自身的软链）。没有 Antigravity 的机器不创建 `~/.gemini/config/`，输出 `skip`。
3. **registry 声明保留为唯一真相源。** `antigravity` 模块仍保留 `config` 声明，`dotf antigravity -c` / `dotf agy -c` 继续走通用 config handler。两个入口写的是同一份 `owner: config:antigravity` 与同一个 config manifest，因此幂等、不会互相 prune，也不存在两套 ownership。
4. **模块名支持 `aliases`。** `modules.yaml` 条目可写 `aliases: [<name>]`；`find_module` 先匹配正规模块名，再匹配别名，所以正规名永远优先。planner 在展开显式模块时把别名收成正规名，计划与 manifest 里只出现正规名。校验拒绝：别名与任何模块名相同、与其他模块的别名重复、自身重复、或写成非字符串 / 空串。
5. **`antigravity` 声明 `aliases: [agy]`**，与它的 CLI 名一致。
6. **桥接改为 `render`，按 HOME 展开绝对路径。** hub server 2.34.0 只认绝对路径，`~/.agents/skills` 会被静默跳过（`customization.go:617`：`must be an absolute path`），尽管它自带的 `json_configs.md` 声明支持 `~/`。源文件因此写 `@HOME@/.agents/skills` 占位符，`config_producers.antigravity` 在部署时替换成实际 HOME；仓库里不出现机器路径，跨机器复用不变。doctor 对非绝对路径的条目单独给 warn，因为这类错误只进 Antigravity 自己的日志，用户看不到。

## 否决的替代方案

- *只改文档，让人记住跑 `dotf antigravity -c`*：问题正是「标准入口 `dotf agents -c` 不覆盖该域」，靠记忆无法消除。
- *把桥接从 registry 移到 `agents/` 源目录*：会多出第二套配置管线，丢掉 config manifest 的 ownership、备份与 takeover 语义，`--on-conflict` 等旗标也要另写一份。
- *在源文件里直接写绝对路径*：换机器或换 HOME 就错，且会把本机路径提交进仓库。
- *保持 `copy` 策略、让用户自己改目标文件*：目标受 manifest 托管，手改下一次 `dotf agents -c` 就会被覆盖回去。
- *让 planner 在 `agents -c` 时顺带展开 `antigravity` 的 config 动作*：`agents` 与 `antigravity` 是并列模块，那样会让 `-c` 语义依赖具体模块清单，profile 与 `--all` 的边界都会变模糊。

## 后果

`dotf agents -c` 现在覆盖 Antigravity 桥接，doctor 的修复提示改为 `dotf agents -c（或 dotf agy -c）`。`tests/test_antigravity_bridge.py` 固化跳过 / 部署 / 幂等 / 接管 / 提示语，`tests/test_registry_aliases.py` 固化别名解析与冲突校验。
