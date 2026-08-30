# 把 evolutions/ 标注为历史归档，统一到 patches 协议

- skill: project-spec-mirror
- risk: low
- 依据: pwd-skill-manager「不与 skill-evolver 混用，以 patches/ 协议为准」

## 问题

目标 Skill 目录下同时存在两套维护记录：`patches/`（28 个目录）与
`evolutions/20260829-complete-mode-notes-mandatory/`（含 `proposal.yaml`、
`*.candidate` 全文副本、`eval.md`、`decision.md`）。两者结构不同、门禁不同，
目录本身没有任何说明。下一个维护者打开这个 Skill 时无法判断该往哪边写，
而 `.candidate` 里保存的是已经过时的 SKILL.md 全文，容易被误读成现行版本。

## 改动

新增 `evolutions/README.md`：说明该目录是 `skill-evolver` 留下的一条历史记录、
改动早已应用、保留仅为追溯依据；现行协议是 `patches/`，不再新增 evolutions 条目；
并点明 `experience/`（输入）与 `patches/`（输出）的分工。

## 非目标

- 不删除、不改写 `evolutions/` 里的任何历史文件。
- 不迁移那条记录到 `patches/`：迁移会造出一份时间戳与事实不符的伪记录。
- 不改 SKILL.md。

## 验证

- `git apply --check --recount`
- `python3 -m unittest discover -s <skill-dir>/tests`
