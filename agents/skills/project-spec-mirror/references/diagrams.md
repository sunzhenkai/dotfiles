# 图表（archify）

镜像里的结构图、流程图、时序、数据流、状态机都委托 skill `archify` 生成。手绘 SVG/Mermaid 不算 archify 产物——记法和校验规则不同，混进来的图下一轮没法再被 validate。同理，archify 的 schema 与渲染器留在它那边，不要拷进本 Skill。

- 上游： [tt-a1i/archify](https://github.com/tt-a1i/archify)（入口 `archify/SKILL.md`）
- 安装：`dotf agents -c` 会按 `agents/skills-defaults.yaml` 装到 `~/.agents/skills`；环境还没有时也可手动 `npx skills add tt-a1i/archify -g -y --copy`
- 类型：`architecture` | `workflow` | `sequence` | `dataflow` | `lifecycle`
- 产物：自包含 HTML 放到 `<spec_root>/diagrams/<slug>.html`；JSON 候选与 HTML 同目录、同 slug（如 `<slug>.json`），便于下次差分。只有 JSON、没有 HTML，不算交付
- `diagrams/INDEX.md`：图 / 类型 / 回答什么问题 / 链到**已经存在的** `.html`。init 骨架可以是空表——空表是诚实的；写成待办清单或链到 archify 的 Skill 目录，会让读者以为有图可看

## 何时画

图表解释的是角色、分叉、状态和时序这几类关系。读者只靠有序列表或表格会跟丢它们时，文字就不够了。反过来，图不是完成度装饰：给每个模块硬画一张结构图，只会稀释真正重要的那几张。

**本轮必须交付**（archify 可用时写出 HTML；不可用则在完成摘要列为未完成）：

- 复杂业务逻辑：分叉、补偿、重试、多角色协作、状态机、一次请求跨多个模块/服务、非平凡数据路径。
- overview 点名的主处理线，凡满足上列之一，配图并链回该 `flows/` 页。
- 用户明确要求的某张图，或“把架构/流程可视化”。

**可以省略：**

- 线性三步、一张表已经说清的模块清单、没有分叉的 CRUD。
- 其余结构/部署图：比表格有明显增益且成本低就随 build 交付；多张或高成本先问用户。

「没有图不算失败」这句是给上面这类可省略的图留的余地，不适用于必配图；复杂业务逻辑缺图时，读者手里就只剩一份读不懂的流程。overview 与切片页只链接已存在的图，不在 Markdown 里重复绘制，也不留占位。

## 执行

1. 读本文件后 **加载并遵循已安装的 `archify` Skill**，按它的 schema/validate/deliver 走；本文件不是它的替代品。宿主会话的 skill 列表里没有 `archify` **不等于未安装**：`Read ~/.agents/skills/archify/SKILL.md`（或 `dotf agents -c` 装到的同等路径），在本轮同一会话按其流程写 JSON、`validate`、`deliver`。
2. 图里的组件、调用、状态都要能追溯到当前镜像的 SOURCE / 模块 / 切片。为了好看发明一条拓扑，等于把读者引向一个不存在的系统。
3. 在 archify Skill 根目录执行（输出路径用镜像里的绝对或相对路径）：

   ```bash
   node bin/archify.mjs validate <type> <spec_root>/diagrams/<slug>.json --json
   node bin/archify.mjs deliver <type> <spec_root>/diagrams/<slug>.json <spec_root>/diagrams/<slug>.html --json
   ```

   质量档次、参数以 archify Skill 为准。非零退出不算已交付。
4. 判定**未安装**的依据是：找不到 `archify/SKILL.md`、找不到 `bin/archify.mjs`，或 node 跑不起来。必配图或用户点名的图因此交不出来时，在完成摘要写明阻塞，INDEX 保持空表或只留已有 HTML。生成假 HTML、或者声称这些复杂逻辑已经讲清，比缺图更糟。
5. 可省略的结构/部署图本轮不做就不做，不在 INDEX 或正文留“暂未生成”占位，只在对话里说明取舍。已经承诺或按上节必须交付的图要有 HTML，不能只留 JSON。

## 与切面的对应

| 要回答的问题 | 优先类型 |
|--------------|----------|
| 系统与邻接、信任边界 | `architecture`（链到 `context/`） |
| 模块、边界、依赖 | `architecture` |
| 进程、部署、网络 | `architecture`（链到 `runtime/`） |
| 切片或发布步骤 | `workflow` |
| 一次请求/调用链 | `sequence` |
| 管道、血缘、存储 | `dataflow`（链到 `data/`） |
| 状态、重试、终态 | `lifecycle` |
