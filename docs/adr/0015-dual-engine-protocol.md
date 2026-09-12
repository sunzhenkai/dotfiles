# 双引擎共存：模块生命周期与制品 Desired Set，统一协议而非合并引擎

`agents` 子系统（src/agents 约 7000 行）自带动词（apply/remove）、schema 生态与 sync 编排，体量与 cli+core+tui 相当，是事实上的「框架中的框架」。但它处理的制品（Skill / MCP Entry）与模块的生命周期不同构：Desired Set = 编目全量 ∪ overlay 启用 − overlay 停用，按机器粒度同步、支持 prune 与两步事务（desired_set 写入 + owned 目标清理缺一不可）；而模块是显式计划驱动的 install/config/doctor 动作。

决定：承认双引擎，统一的是**协议和位置**而非引擎数量——Desired Set / apply / remove 提升为框架级概念（与 module 的 install/config 对偶，CLI 拥有这些动词，TUI 只调用），`src/agents` 是制品引擎的实现；`agents/sync.sh` 等旁路不得自算仓库 ROOT，统一以 `DOTFILES_ROOT`（管线导出）为锚、自算仅作直调兜底。

备选：把 skills/MCP 降为普通模块走 plan_protocol（看似最「统一」，但硬塞会让模块动词与 Desired Set 语义两边变形，否决）；维持 agents 完全自成体系（放任第二套标准，否决）。落地节奏：本 change 只固化 ROOT 锚点与位置约定，协议的进一步上收由后续 change 承担。
