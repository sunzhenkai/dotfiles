# evolutions（历史归档）

本目录只有一条记录 `20260829-complete-mode-notes-mandatory`，由 `skill-evolver` 按它的
proposal / candidate / eval / decision 结构产生。对应改动早已应用到 `SKILL.md` 与
`references/modes.md`，保留它是为了能追溯当时的判断依据。

注意其中的 `*.candidate` 是当时的全文副本，不是现行版本；判断当前规则请读
`SKILL.md` 和 `references/`。

本 Skill 现在的维护协议是 `patches/`：一次改动一个目录，先写 `proposal.md` 与
`change.patch`，`git apply --check` 通过、风险门禁过了才应用，最后写 `result.md`。
两套协议并存会让下一个维护者不知道该往哪写，所以这里不再新增条目；
需要按真实执行经验演进时，同样把结果落成一个新的 `patches/<timestamp>-<slug>/`。

`experience/` 与本目录的关系：`experience/` 记录真实执行中的成功、失败与模式，是输入；
`patches/` 是据此做出的改动，是输出。
