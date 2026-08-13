# 上游 lark-* 路由表（精简）

路径：`~/.agents/skills/<id>/SKILL.md`  
源：https://github.com/larksuite/cli/tree/main/skills  

只据此选 id；**不要**把本表当成操作手册。选定后再 Read 对应 SKILL.md。

## 始终优先

| id | 用途 |
|----|------|
| `lark-shared` | 配置、登录、身份（user/bot）、scope、`_notice` |

## 业务域

| 意图关键词 | id |
|------------|-----|
| 消息、群聊、卡片、加急 | `lark-im` |
| 日程、会议室、忙闲 | `lark-calendar` |
| 云文档内容、docx/wiki 正文、思维笔记 | `lark-doc` |
| 云空间文件/文件夹、上传下载、评论权限 | `lark-drive` |
| Drive 原生 `.md` | `lark-markdown` |
| 电子表格 spreadsheet | `lark-sheets` |
| 幻灯片 | `lark-slides` |
| 多维表格 / Base / bitable | `lark-base` |
| 任务、清单 | `lark-task` |
| 邮件、草稿 | `lark-mail` |
| 通讯录、open_id、找人 | `lark-contact` |
| 知识库空间/节点（结构，非正文） | `lark-wiki` |
| 实时事件订阅 | `lark-event` |
| 历史会议、纪要产物 | `lark-vc` |
| 机器人入会/会中消息 | `lark-vc-agent` |
| 妙记音视频 | `lark-minutes` |
| 已知 note_id 查纪要 | `lark-note` |
| 画板 | `lark-whiteboard` |
| 考勤打卡记录 | `lark-attendance` |
| 审批 | `lark-approval` |
| OKR | `lark-okr` |
| 妙搭应用 | `lark-apps` |
| 找未封装 OpenAPI | `lark-openapi-explorer` |
| 自定义 skill | `lark-skill-maker` |
| 会议纪要汇总报告 | `lark-workflow-meeting-summary` |
| 日程+待办日报 | `lark-workflow-standup-report` |

## 歧义快判

- URL 含 `/docx/` `/wiki/` 且要改**正文** → `lark-doc`；只要节点/空间结构 → `lark-wiki`
- URL 含 `/base/` → `lark-base`
- 「纪要」：有 meeting 记录 → `lark-vc`；妙记媒体 → `lark-minutes`；已有 `note_id` → `lark-note`
- 只登录/授权 → 仅 `lark-shared`，不要加载业务 skill
