# agent-roster-flow 落在一手 Skill，不放进 agent-roster 仓

`agent-roster-flow` 编排的是本仓 Skill（openspec / task-explore / taskflow / grill-with-docs 等），不是名册机制本身。放进 `agent-roster` 仓会让每次改联动路径都跨仓发版；把选人/委派抄进本仓又会和第三方 roster 分叉。因此制品放 `agents/skills/agent-roster-flow/`，选人与委派仍委托第三方 `agent-roster`。
