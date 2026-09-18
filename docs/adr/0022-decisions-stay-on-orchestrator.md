# 决策只发生在 Decision Surface，避免被委派吞掉

`acpx exec` 是一次性、非交互派出。受派方若再问 Track、Assignment、审查范围、是否 apply，问题会进 NDJSON / 超时 / 自动批准，使用者看不到。因此所有需要人点头的选择只在 Orchestrator 当前会话收集，派出时写成 Frozen Input；受派方只执行，不再提问。这与「编排者不得自任执行」不矛盾：禁的是偷偷干活，不是把确认留在本会话。
