# diagrams.md：把风格禁令换成理由与判据

- skill: project-spec-mirror
- risk: medium
- 依据: skill-creator「解释 why，而不是堆 MUST/NEVER；刚性结构是 yellow flag」

## 问题

`references/diagrams.md` 53 行里出现 19 处「必须 / 禁止 / 不得 / 不要」，约每 3 行一处，
是本 Skill 里密度最高的一份。多数是风格类禁令——「禁止把 INDEX 写成待办清单」
「不要为好看而发明拓扑」「禁止假 HTML 或占位」——只说了不许做什么，没说为什么，
执行时无从判断边界，遇到没被枚举到的情形就只能猜。

## 改动

整份重写 `references/diagrams.md` 的措辞层，结论一条不改：

- 保留硬约束，但补上后果：手绘冒充 archify → 图无法再被 validate；
  空 INDEX 是诚实的、待办清单会让读者以为有图可看；
  发明拓扑 → 把读者引向不存在的系统；非零退出不算交付。
- 「本轮必须交付」的清单、可省略清单、执行步骤、类型对照表原样保留。
- 「没有图不算失败」这句改为说明它的适用边界（它是给可省略那一类留的余地），
  而不是简单禁止引用它。

强制性措辞从 19 处降到 5 处左右，字数基本持平。

## 非目标

- 不改任何交付判定：必配图范围、archify 委托关系、HTML/JSON 产物规则、未安装判定依据全部不变。
- 本轮只处理 `diagrams.md`。`routing.md`（46 行 14 处）与 `modes.md`（180 行 23 处）
  留待后续单独 patch，避免一次改动跨越太多语义面。

## 验证

- `git apply --check --recount`
- `python3 -m unittest discover -s <skill-dir>/tests`，其中
  `test_diagrams_cover_complex_logic_without_fake_delivery` 依赖的四个标记
  （「复杂业务逻辑」「本轮必须交付」「不能只留 JSON」「没有图不算失败」）必须保留
- 重新统计强制性措辞密度
