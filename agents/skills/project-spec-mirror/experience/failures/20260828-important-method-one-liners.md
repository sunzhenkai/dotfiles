# important 把核心方法写成一句话

- Date: 2026-08-28
- Kind: failure
- Skill: project-spec-mirror
- Context: detailed / important 写模块核心符号时，把方法层理解成「名字 + 一句话」

## What happened

Agent 补上了文件表覆盖，但仍把核心方法写成一句话职责，并漏列工具方法。测试方法在 complete 下被展开成用例步骤。

## Lesson

- 核心方法必须梳理完整逻辑（步骤、分支、成败、副作用），不是一句话点到为止。
- 工具方法可以简述，但必须列名，不得漏列。
- 测试方法只简述覆盖范围；important 与 complete 都不得写断言步骤。
