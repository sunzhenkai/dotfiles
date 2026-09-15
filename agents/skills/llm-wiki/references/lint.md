# Lint

确定性检查由 `scripts/lint_wiki.py` 执行。LLM 负责解释、排序和修复，不要只看一遍报告就算完成。

```bash
python3 <this-skill>/scripts/lint_wiki.py "{WIKI_ROOT}"
python3 <this-skill>/scripts/lint_wiki.py "{WIKI_ROOT}" --json
python3 <this-skill>/scripts/lint_wiki.py "{WIKI_ROOT}" --write-index
```

`--write-index` 根据 typed 子目录与 frontmatter 重建 `wiki/index.md`，不改其它文件。

## 检查码

| 码 | 级别 | 含义 |
|----|------|------|
| `dead_link` | error | `[[link]]` 或 `[text](path)` 目标不存在 |
| `missing_frontmatter` | error | 业务页缺 title / type / date |
| `log_format_invalid` | error | `log.md` 条目前缀不符合 `## [YYYY-MM-DD] action \| description` |
| `log_date_decreasing` | error | 日志日期递减（违反仅追加） |
| `type_dir_mismatch` | warning | `type` 与所在 typed 目录不一致 |
| `misplaced_wiki_page` | warning | 业务页不在 typed 子目录 |
| `duplicate_page` | warning | 同目录下文件名归一化后重复（去空格/`_`/`-`/全角空格后小写） |
| `entity_concept_coupling` | warning | 概念标题把实体名绑到抽象概念上 |
| `orphan_page` | warning | 无入链；系统页与 `wiki/sources/` 不计入。系统页上的链接仍查死链，但不计入入链（否则 index 会掩盖孤立页） |

不同目录的同名文件不报 `duplicate_page`。

## 修复顺序

先 error，后 warning。一页多问题一次改完。改前先读全文，避免为消警告丢掉信息。

**死链**：先找是否改名或 slug 不同；不确定就提问或标开放问题，不要随便建空页。更倾向于把链接改到正确页，而不是删掉链接。

**Frontmatter**：`type` 可从目录推断，但不要随便改身份字段。缺 `date` 用修复当日。

**日志**：只改格式与日期顺序问题；不删条目、不改历史含义。

**孤立页**：判断是否本来就该少入链（临时 query 可推迟）。否则从 overview、相关实体或概念补 `[[wikilink]]`。

**错位 / 类型不一致**：让 `type` 与目录一致；移动后更新旧路径上的链接。

**实体-概念耦合**：改成中性概念标题，实体作为案例链入；更新旧 wikilink。不要为消警告删概念正文。

**重复页**：读两页后合并或改名，保留独有事实。

## 脚本做不到的（需 LLM）

- 页面间事实矛盾
- 过时主张
- 正文提到但尚未建页的概念
- 缺失的交叉引用（入链检查只覆盖已有链接）

`organize` 与 `lint` 可建议这些项，但不要假装脚本已经查过。

## 完成标准

- [ ] lint 报告 0 error
- [ ] 死链已解析（改链或确认目标）
- [ ] 业务页 frontmatter 合法
- [ ] `wiki/log.md` 格式合法且日期非递减
- [ ] warning 已修或有意推迟并说明
- [ ] 关键修复页已回读
