# GATE — 薄门禁

BUILD 的出口检查：一组二元必过项。任何一项 NO，回到 BUILD 修复，禁止进入 REVIEW、禁止输出「完成」。只检查客观、可验证、快速的项目，不做主观审美，不做全面审查。

## 必过清单

- [ ] lint 通过
- [ ] typecheck 通过
- [ ] build 通过
- [ ] 本次组件状态覆盖：default / hover / focus-visible / active / disabled / loading / error / empty
- [ ] 375px 和 1440px 截图已生成
- [ ] 无横向滚动
- [ ] console 无新增 error
- [ ] network 无新增 error
- [ ] 键盘可操作，focus-visible 可见
- [ ] 表单错误靠近字段且 aria 基本正确
- [ ] 未修改无关文件

## 输出格式

```md
## GATE
- lint: PASS / FAIL
- typecheck: PASS / FAIL
- build: PASS / FAIL
- 状态覆盖: PASS / FAIL（缺失：...）
- 截图: PASS / FAIL
- 横向滚动: PASS / FAIL
- console: PASS / FAIL
- network: PASS / FAIL
- 键盘/focus: PASS / FAIL
- 表单 aria: PASS / FAIL
- 无关文件: PASS / FAIL

结果：PASS → 进入 PHASE 2 / FAIL → 回到 BUILD
```

FAIL 时只修复失败项，修复后重新过 GATE。
