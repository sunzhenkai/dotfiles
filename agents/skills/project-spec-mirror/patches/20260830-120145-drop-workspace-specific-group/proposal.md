# 去掉「同 group」这类工作区特例表述

- skill: project-spec-mirror
- risk: low
- 依据: pwd-skill-manager 公开性约束（只加入跨项目、跨环境仍成立的规则）

## 问题

SKILL.md build 第 7 步要求「build 前先 grep 同 group 已镜像仓的 `modules/*/notes/` 主题列表做参考」，
`evals/cases.yaml` 的 `complete-mode-notes-mandatory` 把这条写成了 must，并用
`spec/<group>/<repo>/modules/...` 的路径形状做判据。

「group」是本地多仓工作区（`spec/<group>/<repo>/`）的组织方式，不是这个 Skill 定义的概念。
公开安装的使用者无从判断自己有没有 group，也无从判断「同 group」指哪些仓，
于是这条要么被忽略、要么被误解成必须去找别的仓库。用无条件 must 表述一个可能不存在的前提，
是在给自检表制造假失败。

## 改动

1. SKILL.md 第 7 步：改为条件式——本工作区已有其他项目镜像时才去对齐主题维度，
   并说明为什么值得看（省得每个仓从零想选题）；没有可参照镜像时直接按触发条件枚举。
2. `evals/cases.yaml` 的 `complete-mode-notes-mandatory`：
   - notes 路径判据改为 `<spec_root>/modules/<m>/notes/*.md`，不再假设 `spec/<group>/<repo>/` 布局；
   - grep 那条改为条件式，没有可参照镜像时按 5 类触发条件自行枚举也算通过。

## 非目标

- 不动 `experience/`、`evolutions/`、历史 `patches/`：它们记录当时真实发生的事，不是现行规则。
- 不改 `notes/` 的 5 类触发条件本身，也不改 `complete` 下 notes 必建的结论。

## 验证

- `git apply --check --recount`
- `python3 -m unittest discover -s <skill-dir>/tests`
- grep 确认生产文件（SKILL.md / references / evals）不再出现无条件的「同 group」要求
