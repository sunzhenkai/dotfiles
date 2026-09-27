# design 角色补控件高度分档依据规则

- target: agents/skills/role-based-reviewer
- mode: update
- patch: 20260927-171900-density-tier-justification
- risk: medium
- status: proposed

## Intent

真实案例：某紧凑型界面（正文 14px，icon 按钮 30px、头像 22px）把遗留默认输入框高度 36px 直接升格为「常规档」token，与全局 32px 并存，弹窗输入框明显偏高。一致性检查全绿——静态门钉住 token 值，浏览器契约断言「控件跟 token 走」，两道门验证的都是「实现符合实现自己」，token 档位本身永远验不到。评审者核对「符合契约」而不问「档位划分是否成立」，把可感知的失调误判为「设计内」。

要改变的行为：design.md 第 9 节新增两条通用规则——

61. 🟡 [代码] 控件高度分档默认单档；出现第二档 MUST 有与正文字号、整体密度的比例依据（写在 token 注释或设计文档里），「有的页面历来是这样」不算依据
62. 🟡 [代码] 禁止把遗留默认值 / 框架默认值直接升格为设计档位；引入或保留任何尺寸档位时 diff 中应能找到推导（字号倍数、密度基准或可读注释），而非只有取值

非目标：不改 56–60 条；不规定具体像素或比例数值（数值由各项目设计决定）；不改 quality-profile 四问（61/62 是评审侧的档位审查规则，四问是交付侧的画像字段，互补）。

## Conflict check

- 与 56 条（同上下文同高）互补：56 管「档内一致」，新条目管「档位本身是否该存在」。
- 与 57 条（间距走 token）同构：token 化解决「值散落」，新条目解决「值从哪来」。
- 通用性：不出现项目名、类名、像素值；「遗留默认值升格」是可跨项目复用的失败模式。

## Rationale

token 化与契约测试解决的是「一致性可机械验证」，但值的来源仍靠设计判断；漏掉这一层，验证体系会变成循环论证（实现断言实现）。把「档位最小化 + 推导可见」写成 `[代码]` 可判定条目后，评审在 diff 层即可拦截「围绕现状倒推分类」这类伪设计决策。

## Files

- `agents/skills/role-based-reviewer/references/roles/design.md` — 第 9 节末尾追加 61、62 条

## Validation

- 应用前：`git apply --check --recount agents/skills/role-based-reviewer/patches/20260927-171900-density-tier-justification/change.patch`。
- 应用后：`git diff --check`；diff 与 proposal 一致；无项目专有名词 / 本机路径 / 凭据。
- 本轮按 delivery-loop 失败归因执行（skill gap：design 清单缺档位依据规则），medium 门禁视同已确认，应用后补 `result.md`。
