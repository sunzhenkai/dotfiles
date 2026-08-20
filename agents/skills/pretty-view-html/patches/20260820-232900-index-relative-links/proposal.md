# 修正索引链接的相对路径基准

- target: agents/skills/pretty-view-html
- patch: 20260820-232900-index-relative-links
- risk: medium
- status: proposed

## Intent

明确所有生成页面，尤其是根聚合页和内容包索引，必须以当前 HTML 文件所在目录为基准计算本地链接；支持输出到任意目录或嵌套层级，不假设页面位于仓库根或站点根。

非目标：不改变外部 HTTP(S) 链接、文件组织、归类流程或导航形态。

## Conflict check

现有规则已要求 `href` 和 `src` 使用相对路径，但没有规定相对基准，也没有明确禁止以 `/` 开头的站点根路径。本次是行为澄清，不改变既有职责；与自定义输出路径规则一致。

## Rationale

静态 HTML 可能从任意目录直接打开或整体搬移。以当前文件目录计算 `./`、`../` 链接，才能保证索引、内容页和资源在非根输出路径下仍然可达，并可通过静态检查验证。

## Files

- `agents/skills/pretty-view-html/SKILL.md`：增加本地链接基准、嵌套路径示例和完成检查。

## Validation

- 应用前运行 `git apply --check --recount`。
- 应用后运行 `git diff --check -- agents/skills/pretty-view-html`。
- 核对相对路径规则覆盖索引、内容页、资源和自定义输出目录。
