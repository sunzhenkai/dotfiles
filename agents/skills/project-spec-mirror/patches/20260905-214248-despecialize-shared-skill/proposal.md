# 去掉共享 Skill 的特例化内容

- target: agents/skills/project-spec-mirror
- patch: 20260905-214248-despecialize-shared-skill
- risk: medium
- status: proposed

## Intent

按已确认的评审收口：

1. 历史 `experience/` / `evolutions/` 摘要去掉真实仓名与本机同步步骤，并标 `superseded`，不得驱动现行 briefing/reconstructable。
2. 机械门禁中英兼容：占位「待 build」/ to be built；表头 `能力`/`Capability`；泄漏「完整逻辑」/ full logic、`## 文件`/`## Files`；清单版本扫描补 Cargo.toml / pyproject.toml 等。
3. 旧金字塔迁就移到 `references/appendix.md`，主路径只留 `layout=legacy` → rebuild 指针。
4. 回复语言改为沿用用户语言；archify 加载路径不写死家目录。

非目标：不恢复 complete/notes；不改 6 命令与 finalize 唯一收尾。

## Conflict check

- 与现行双读者验收无冲突；被改写的 experience 原本就在教已删除档位。
- `*.candidate` 仍是旧全文副本，README 已写明勿执行；摘要文件不再含私有仓名。

## Rationale

共享 Skill 只能保留跨项目仍成立的规则。中文短语当唯一正则、以及旧任务档案里的仓名，都会让安装者误伤或泄密。

## Files

- `SKILL.md` `references/layout.md` `references/appendix.md` `references/checklist.md` `references/diagrams.md`
- `scripts/specctl.py` — stub / leak / CODE_EXTS
- `experience/` `evolutions/` 可执行摘要
- `evals/cases.yaml` `tests/`

## Validation

- `git apply --check --recount`
- `python3 -m unittest discover -s agents/skills/project-spec-mirror/tests`
