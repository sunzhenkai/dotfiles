# 全量 skill 编目收敛到一份 `agents/skills.yaml`，按 group 组织，取消 default 开关

第三方默认清单（`skills-defaults.yaml`）与短名映射（`skills-map.yaml`）合并为一份 **skill 编目** `agents/skills.yaml`，lock 相应改名 `agents/skills.lock.yaml`。理由：两份文件维护重复，且打平的 id 列表无法表达来源聚合、包形态与别名。

编目**按 group 组织**：

- 组声明来源属性：`type: first-party | third-party`；第三方还要 `source: registry | github` 与 `package`。
- 组成员只写安装 id；**组名兼作 CLI 展开单位**（`dotf skills -i <group>` 展开整组）。
- id 是 desired_set / lock / overlay 唯一认的键，全局唯一。
- 一手条目来源是仓库内 `agents/skills/<id>/`，不带 package/revision/hash，目录即真相。
- 第三方条目 revision/hash/license/audit 只在 lock；编目只引用。

## 取消 default：编目内即默认安装

**没有"是否默认安装"字段。** 编目里的条目就是自动全量安装（`dotf agents -c`）的内容。不想装就**注释掉**该条目：注释掉即不在编目内，于是既不自动装，也不能经 overlay / `dotf agents skill apply` 引用；`dotf skills -i <name>` 只会把它当普通名字透传给 npx。

规则：

- Desired Set = 编目内全部 id ∪ overlay 启用 − overlay 停用。
- overlay 只能启用/停用**编目内**的 id；编目外（含"锁着但已注释"）一律拒绝。
- 一手 skill 的真相源是编目：`agents/skills/<id>/` 存在但未编目 → fail closed；反向亦然。

## 名字解析

`dotf skills -i/-r <name>` 与 `dotf agents skill apply/remove <name>` 顺序为：**先 group → 再 skill id → 最后透传 npx skills**。group 与 id 同名时按 group，并打印提示。对一手 id 使用 `dotf skills -i` SHALL 拒绝并提示改用 `dotf agents skill apply <id>`。

本 ADR 取代 ADR-0007 关于「默认集合组成来源」的表述；overlay 语义与 prune 绑定仍以 ADR-0003 / 0007 为准。
