# skills-archive

已从编目下线、不再安装的一手 Skill。生产内容与历史 `patches/` 保留于此，便于查阅与恢复。

## 恢复

1. 把 `<name>/` 移回 `agents/skills/<name>/`
2. 在 `agents/skills.yaml` 的 `dotfiles` 组加入该 id
3. 跑 `dotf agents -c` 同步到各 layout

不要手改 `~/.agents/skills/` 等安装产物。

## 条目

| 名称 | 下线原因 |
|------|----------|
| `task-design` | 设计流程并入 `task-explore` 的 `design` 阶段；文档落在任务目录，不再写 `docs/design/` |
