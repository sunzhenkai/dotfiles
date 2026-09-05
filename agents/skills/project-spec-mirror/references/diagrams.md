# 图表（archify）

仅在复杂业务逻辑或用户点名要图时读本文件。产物放 `briefing/diagrams/`。手绘 SVG/Mermaid 不算交付。不要拷 archify schema。

- 上游：[tt-a1i/archify](https://github.com/tt-a1i/archify)
- 类型：`architecture` | `workflow` | `sequence` | `dataflow` | `lifecycle`
- HTML + 同 slug JSON；不能只留 JSON
- INDEX 只链已存在的 `.html`

**本轮必须交付：** 复杂业务逻辑（分叉、补偿、状态机、跨系统时序、非平凡数据路径）；overview 点名的这类主处理线。线性三步可省略。「没有图不算失败」只适用于可省略的图。

执行：加载已安装的 `archify` Skill（按各 agent 的 skills 目录查找，不要写死家目录），然后：

```bash
node bin/archify.mjs validate <type> <spec_root>/briefing/diagrams/<slug>.json --json
node bin/archify.mjs deliver <type> <spec_root>/briefing/diagrams/<slug>.json <spec_root>/briefing/diagrams/<slug>.html --json
```

找不到 CLI 或 node：回执列为阻塞，禁止假 HTML。
