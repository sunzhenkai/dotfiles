# skill 目标收敛为一处 layout 注册表；apply 覆盖全部来源；冲突补备份出口

三个问题一起处理，因为它们都出在"skill 装到哪、由谁装"这件事没有单一表达上。

**一、apply 不装第三方 skill（缺陷）。** `desired_ops` 只调 `sync_skills` + `sync_kiro_skills`，而这两个只遍历仓库内 `agents/skills/<id>/`。`codebase-design` 这类 Locked Skill 由 `defaults.install_defaults` 经网络获取后安装，apply 从不调用它。于是 `dotf agents skill apply codebase-design` 写了 overlay、报了成功、磁盘上什么都没装。根因不是漏了一个函数调用，而是 apply 手抄了 `agents -c` 四步里的两步：同一个"使 Desired Set 存在"的语义有两份实现，必然漂移。

决定：apply 按 id 所属来源补齐 —— 一手 id 走仓库目录，第三方 id 追加一次锁定获取（`acquire_all` 按 lock 条目逐条 `git fetch`，所以一手 apply 不付网络代价），OpenSpec 的 `openspec-*` 仍只由 `agents -c` 安装。同时把失败摘要从"三 rc 或成一个布尔"改成按 layout 收集 `(label, detail)`，`RESULT` 的 reason 带上具体目标与原因（`skills: service-manager/SKILL.md: owned target was modified locally`）。

**二、目标从两处硬编码收敛为一处注册表。** 加 Claude Code 目标前，"两个目标"分别硬编码在 `sync.py`、`defaults.py`、`openspec_skills.py`、`doctor.py`，每处自带一套 owner 前缀常量；照抄加第三个会变成八处。新增 `src/agents/layouts.py` 作为唯一真相源：`LAYOUTS`（shared / kiro / claude）+ 由 `(layout, source)` 派生 owner 与 identity 前缀。owner 前缀**必须**逐 layout 互不重叠 —— runtime manifest 是所有 layout 共用的一份，`apply_owned_plan` 按 owner 前缀决定"保留哪些既有条目"，两个 layout 共用前缀会互相把对方的条目从 manifest 里删掉。shared / kiro 的前缀逐字保持不变，否则升级当天全机目标被判为 ownership-identity 冲突。

Claude Code 目标 `~/.claude/skills/` 收全部三类来源。它自己消费 `$ARGUMENTS`（无占位符时按 `ARGUMENTS: <value>` 追加），所以不做 Kiro 式的显式注入，走与 shared 相同的渲染；`synced` 是 Claude Code 的保留目录名（它自己往那里放 claude.ai 同步来的 skill，并跳过同名用户 skill），编目里用它会 fail closed。

**三、冲突补一个显式出口。** 默认仍 fail closed：owned 目标漂移时报告并保留。新增 `--on-conflict=backup`（`block` 为默认）覆盖**只有**两类可判定为"本机改过已受管目标"的冲突：内容漂移与 mode 漂移。实现上把它们在编译期改判为 update，写路径复用既有的 `atomic_write(backup_root=...)`，旧字节留在 `${XDG_STATE_HOME:-~/.local/state}/dotf/backups/<run-id>/<home 相对路径>`。不安全类型（symlink 等）、manifest 不可解析、所有权不符、无所有权目标、越界目标**永远** fail closed —— 这些意味着 dotf 不知道自己要覆盖什么；`deconfig` / `uninstall` / `remove` 的 prune 方向同样不受该开关影响。（Unowned Target 的显式接管见 ADR-0020，不经本开关。）

开关的传输沿用 `DOTF_DEEP` 的做法：CLI 解析 `--on-conflict` → `Ctx.export()` 写 `DOTF_ON_CONFLICT` → handler 子进程读取。不新增 plan 协议字段。

随之更新：`src/agents/layouts.py`（新增）、`managed_runtime.py`（`on_conflict` 策略、`remediated`、保留名守卫）、`sync.py` / `defaults.py` / `openspec_skills.py` / `doctor.py`（遍历 `LAYOUTS`）、`desired_ops.py`（来源补齐 + 逐 layout 失败摘要）、`src/dotf_cli/{__main__,runner,commands}.py`、`scripts/modules/agents/sync.sh`、`agents/README.md`、`docs/Dotfiles.md`、`CONTEXT.md`（新增 Skill Layout 词条、Conflict 补出口）。

后果：`dotf agents -c` 首次运行会往 `~/.claude/skills/` 写全部受管 skill。layout 之间的成败相互独立（一个目标冲突不再阻断其它目标写入），失败仍由 `RESULT` 传播。若第四类目标出现（如同类的第三方 CLI），加一条 `SkillLayout` 即可，不再需要改四处。
