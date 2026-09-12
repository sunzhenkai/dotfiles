# 模块产出按物种（`kind`）显式建模，校验器强制「声明 ↔ Handler」对齐

模块的本机产出早已分化为两个物种：负责把软件装到本机的模块（有 `scripts/modules/<name>/` Handler 目录）与只部署配置的模块（纯 registry + `config/` 源，零 Handler）。此前这一二分只靠 `install:` 字段隐式表达，校验器无法判定「该有而没有」与「不该有而有」：Handler 目录是否该存在、目录里允许什么文件，都没有契约约束，Codex/OpenCode 的 Handler 目录里甚至长出了 Python（`merge_config.py`）。

决定：registry 显式声明 `kind: binary | config`（`artifact` 为保留值，供未来 skills/MCP 制品型模块使用）。`binary` ⇔ 声明 install 能力 ⇔ Handler 目录内有 `install.sh`；`config` ⇔ 无 install 能力 ⇔ 不得有 `install.sh`。校验器（`dotf_core.registry validate`）在计划生成前拒绝缺失 `kind`、物种与能力/目录不一致、以及 Handler 目录内的非 `.sh` 文件；需要 Python 的合并/渲染逻辑一律由内核（`dotf_core.config_producers`）提供。

备选：继续用 `install:` 隐式表达（无法支撑校验，否决）；每模块自包含目录的聚合方案（ADR-0011 已否决，config 分类导航会丢、纯配置/纯安装模块会出现空目录，不重启）。注意 `kind: config` 不禁止专用 `config.sh` 处理器——它是 CONTEXT.md Handler 定义内的合法配置触点，被禁的只有 `install.sh`。
