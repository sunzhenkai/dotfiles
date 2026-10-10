# ui-templates-audit-overreach

## 性质
archify 与 ui-template-author 的 lock 推进被「过宽」审计规则误阻断。需走 skills-store 三件套（proposal + change + result），让 rules 精度收紧后，下轮 `make skills-lock-update` 能继续推进。

## 来源
- 触发任务：`ongoing/update-external-skills`（2026-10-10，步骤 1.5）。
- 证据：`tasks/ongoing/update-external-skills/evidence/lock-update.log`（`archify` / `ui-template-author` 两段）。

## 误报类别（已知）
1. `hardcoded_secret`：命中变量名含 `token` 的渲染源（几何令牌 / 缓存键 / 设计系统 `project_token`）。
2. `jailbreak_role`：命中英文学术/合同注释里的「contract / fallback / same as」等普通词。
3. `bypass_approval`：命中反向写「必须显式 opt-in 才能关沙盒」的测试断言。

## 涉及规则源
- 仓库：`sunzhenkai/solo-skills` 仓下的 `skills/skills-store/`。
- 需走该仓的 `skills/skills-store/patches/{date}-{topic}/` 三件套：proposal / change / result，并把对应 `tests/test_audit_skill.py` 回归用例留好。

## 验收
- `FAIL_ON_WARN=1 make skills-lock-update` 把这两条 skill 推到 HEAD（`7f483b61e8f6` for archify，`3d5fc437edc4` for ui-templates-skill）。
- 其它非 overreach 类 rule 的拦截面没退化。

## 不在本子任务里
- 改 lock；改 audit evidence。
- 删除或弱化现有规则；只调精度。
