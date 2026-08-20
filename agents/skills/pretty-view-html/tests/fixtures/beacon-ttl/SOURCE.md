# 灯塔网关 SEV-1：signed-url TTL 单位事故

这份草稿是 pretty-view-html 阅读页展示测试的源稿。灯塔网关（Beacon Gate）是虚构的个人文件分发网关。2026-08-12 的 TTL 单位错误、当晚热修复、以及热修复合入前的审查，是**同一件事**：已吊销链接仍能下载，根因在 `ttl_ms` 被当成秒写入 Redis。读者对象是值班工程师、跟动作项的研发，以及将要合入 `PR #1843` 的评审人。不是对外新闻稿，也不另写一份独立 code review。

## 结论

1. 2026-08-12 19:14–20:01（UTC+8）窗口内，已吊销的 `signed-url` 仍能下载私有文件，最长存活约 47 分钟。
2. 根因是 PR `#1842` 把内部时钟统一成毫秒，调用值改成 `ttl_ms`，但 Redis `EXPIRE` 仍按秒解释，过期窗口被放大约 1000 倍。
3. 19:31 的缓解（停发 + `EXPIRE 90`）堵住新泄露；20:01 热修复 `PR #1843` 让新签发回到约 90s。缓解不等于根因已关。
4. 热修复**带条件可合入**：`ttl_ms <= 0` 必须先拒绝；跨日边界、token 日志、`expire-mismatch` 可在合入后 24h 内补，但要登记。结构债不因热修复关闭。

## 目录

1. [影响范围](#1-影响范围)
2. [时间线](#2-时间线)
3. [根因](#3-根因)
4. [为什么检测失败](#4-为什么检测失败)
5. [缓解与热修复](#5-缓解与热修复)
6. [热修复审查](#6-热修复审查)
7. [测试覆盖](#7-测试覆盖)
8. [动作项](#8-动作项)
9. [残留风险与未决项](#9-残留风险与未决项)

## 1. 影响范围

事故等级 **SEV-1**。灯塔网关的私有文件下载依赖短时 `signed-url`；注销、权限回收和「链接过期」都走同一条 Redis TTL。TTL 一旦按秒解释，用户面的「已吊销」就不成立。

产品面：灯塔网关给桌面客户端签发一次性下载地址，默认存活 90 秒，过期后对象存储侧仍保留文件，但网关必须拒绝。共享文件夹、外链审批、管理后台的「立即失效」按钮，最终都调用 `persistSignature` 写 `sig:{id}`。

| 面 | 事实 | 窗口 / 范围 |
|----|------|-------------|
| 用户面 | 已注销或权限已回收的下载链接仍返回 200 | 19:14–20:01 UTC+8 |
| 数据面 | 私有对象未被改写；问题是授权窗口，不是内容损坏 | 同上 |
| 会话面 | `session.go` 写入的 TTL 名义 90s，实际约 90_000s（约 25 小时） | 部署 `beacon-gate@2.14.0` 起 |
| 规模 | 受影响签名约 1.2k 条；确认被二次使用 37 条 | 审计日志 `audit.signed_url.reuse` |
| 地域 | `nrt-1` 先行滚动，`sin-1` 尚未接到 2.14.0 | 只 nrt-1 进入 SEV-1 |
| 客户面 | 受影响工作区 11 个；含 2 个开启外链审批的团队空间 | 支持工单 BG-4417、BG-4419 |

二次使用 37 条的拆分：同一浏览器会话内刷新 21 条，注销后再打开 9 条，把链接发给另一设备 7 条。后两类是真正的越权窗口。对象存储访问日志与网关审计可以对齐到同一 `sig` 前 8 位。

> [!WARNING]
> SEV-1 不是因为数据丢失，而是因为「已吊销」在用户面不成立。私有文件在过期前提前泄露，等同于鉴权失效。不要把本事故写成存储损坏或 CDN 缓存问题。

## 2. 时间线

按值班台账记录，时间均为 UTC+8。变更窗口的负责人是认证值班（`auth-oncall`），缓解由网关值班执行。

| 时间 | 事件 | 证据 |
|------|------|------|
| 18:22 | `beacon-gate@2.14.0` 开始滚动。变更说明：会话与签名 TTL 统一为毫秒，关闭 `ttl_sec`。 | 发布单 REL-214 |
| 18:51 | nrt-1 滚动完成。`signed_url_issued` 计数正常，无错误率跳变。 | 仪表盘 |
| 19:14 | 用户反馈：注销后旧 `signed-url` 仍能打开附件。工单 BG-4417。 | 支持 |
| 19:22 | 值班复现。Redis `TTL sig:7f3a9c12` 返回 `89910`，单位被当成秒。 | `redis-cli TTL` |
| 19:26 | 对照代码：`BuildSignedURL` 写入 `ttl_ms := 90_000`，`Expire` 乘的是 `time.Second`。 | `session.go` |
| 19:31 | 切流量：停止签发新链接，对现存 `sig:*` 执行 `EXPIRE 90`。扫描到 1184 个键。 | 缓解脚本 |
| 19:38 | 审计回放启动。确认 19:14 之后有二次使用，当时未完成计数。 | 审计 |
| 19:48 | 根因写进事故频道：调用方单位错误，不是 Redis 配置，也不是时钟回拨。 | 值班记录 |
| 20:01 | 热修复 `PR #1843` 上线 `beacon-gate@2.14.1`。19:31 之后无新的二次使用。 | 发布单 REL-215 |
| 20:18 | 二次使用最终计数 37。法务开始看通知口径。 | 审计汇总 |
| 20:40 | 全量扫描残留键，最长 TTL 已压回 90s。`TTL > 120` 为 0。 | 缓解脚本第二次 |

阅读这条时间线时，19:31 的缓解已经堵住新泄露；根因确认发生在缓解之后，热修复在 20:01 才让新签发恢复正确。不要把「已缓解」写成「已修复」，也不要把热修复写成另一次无关变更。

缓解脚本的关键步骤（已在 nrt-1 执行完毕）：

```bash
redis-cli --scan --pattern 'sig:*' | while read -r key; do
  redis-cli EXPIRE "$key" 90
done
```

## 3. 根因

PR `#1842`（`ttl: unify session clock to milliseconds`）把内部时钟统一成毫秒，避免 `time.Second` 与 `time.Millisecond` 混用。`BuildSignedURL` 改为持有 `ttl_ms`，但 `persistSignature` 仍按旧注释「传给 Expire 时乘 Second」换算。

出错代码（`beacon-gate@2.14.0`，`internal/auth/session.go`）：

```go
ttl_ms := 90_000
if err := rdb.Expire(ctx, key, time.Duration(ttl_ms)*time.Second).Err(); err != nil {
    return err
}
```

问题不在 Redis，而在调用方：`ttl_ms` 已经是毫秒整数，却乘上 `time.Second`。`Expire` 的参数类型是 `time.Duration`，这里实际写入约 90_000 秒。

调用链：

1. `BuildSignedURL` 计算墙钟 `expires_at = now + 90s`，同时把 `90_000` 交给 `persistSignature`。
2. `persistSignature` 只负责 Redis TTL，不再看 `expires_at`。
3. 网关校验先查 Redis，再比对墙钟。Redis 仍活着时，墙钟过期只记一条 debug 日志，不拒绝下载。这是旧兼容：客户端时钟不准时仍允许短窗口。单位错误后，兼容路径变成「Redis 活着就放行」。

正确写法应是 `time.Duration(ttl_ms)*time.Millisecond`，或直接传 `90*time.Second` 并禁止再引入裸整数。热修复采用前者，与 `#1842` 的毫秒化方向一致。

同一 PR 改了测试的期望注释（「90s」），但断言仍只检查 `Expire` 被调用，不检查 duration 量级。这不是测试「没跑」，而是测试在测错的东西。

## 4. 为什么检测失败

四道本应拦住的闸都按「调用发生了」而不是「过期窗口对不对」来设计。

- 单元测试 mock 了 Redis，只断言调用次数，不断言 `time.Duration` 的数量级。`TestExpireCalled` 在 `#1842` 前后都是绿的。
- 集成测试的 TTL 等待用的是 90ms 轮询，键在测试结束前不会到期，绿的是假象。没有人断言「90s 后键必须消失」。
- 仪表盘有 `signed_url_issued` 和 `signed_url_rejected`，没有 `expire-mismatch`：名义 TTL 与 Redis `TTL` 差一个数量级时无人报警。19:14 之前错误率也没有上升，因为请求仍返回 200。
- code review 看了「单位统一」的方向，抽查了 `BuildSignedURL` 的 `expires_at`，没有打开 `persistSignature` 看换算。`ttl_ms * time.Second` 在 diff 里像是一条普通的 Expire 调用。

预发有过一次「链接稍晚过期」的工单（BG-4390，8 月 9 日），当时被解释成客户端缓存，没有对照 Redis `TTL`。那是漏报，不是新根因。

## 5. 缓解与热修复

立即（已完成）：

1. 停止签发，对 `sig:*` 重写 `EXPIRE 90`。nrt-1 1184 个键，最长原 TTL 约 89940s。
2. 吊销 19:14 之后仍被使用的 37 条审计命中：写 `revoked:{sig}`，对象存储侧加 24h 拒绝名单。
3. 热修复 `PR #1843`：`persistSignature` 改为按毫秒换算，随 `beacon-gate@2.14.1` 在 20:01 上线。

热修复当前补丁：

```go
ttl_ms := 90_000
if err := rdb.Expire(ctx, key, time.Duration(ttl_ms)*time.Millisecond).Err(); err != nil {
    return err
}
```

方向正确：名义 90s 与 Redis TTL 重新对齐。热修复的范围只是这一处换算，不是整次 TTL 毫秒化重构，也不清扫其他模块是否还有 `ttl_ms * time.Second`。

短期不在热路径夹带，但属于同一事故的关闭条件：给 `Expire` mock 增加 duration 量级断言；补跨日边界；拒绝 `ttl_ms <= 0`；日志去掉完整 token。结构项是 `expire-mismatch` 指标。

## 6. 热修复审查

审查的是同一事故的热修复 `PR #1843`，不是另起一份评审文档。已看文件：`internal/auth/session.go`、`internal/auth/session_test.go`、`internal/auth/redis_expire.go`。未看：网关其他模块是否还有 `ttl_ms * time.Second`——那是动作项，不在本 PR。

合入目标：让 `signed-url` 的 Redis TTL 回到约 90s，并且热路径不再接受非法 TTL。结论与文首一致：带条件可合入。

### 6.1 阻断：零值与负值仍会写入

`internal/auth/session.go:142` 在换算前没有拒绝非法 `ttl_ms`。测试里用 `ttl_ms := 0` 时，`Expire` 仍被调用。

```go
func persistSignature(ctx context.Context, key string, ttl_ms int64) error {
    return rdb.Expire(ctx, key, time.Duration(ttl_ms)*time.Millisecond).Err()
}
```

Redis 对 0 duration 的行为与「立即过期」并不总一致；负值会变成巨大的 uint 转换风险。热修复必须在调用 `Expire` 前拒绝 `ttl_ms <= 0`，并覆盖该分支。不修则带条件结论不成立，SEV-1 不能从热路径关掉。

### 6.2 主要：跨日边界没有测试

`internal/auth/session_test.go` 只在同一假时钟下断言 90s。没有覆盖 23:59 → 00:01 的签发与校验。灯塔网关的签名校验用的是墙钟 `expires_at`，TTL 与墙钟任一偏差都会在跨日复现成「链接已过期但 Redis 仍活着」，或反过来。

建议：用固定 `time.Time` 在 `2026-08-12 23:59:30` 签发，拨到次日 00:00:30 再取，断言 Redis TTL 与 `expires_at` 同向收缩。可在合入后 24h 内补，必须登记在动作项。

### 6.3 主要：日志可能带完整 token

`internal/auth/session.go:168` 的失败路径：

```go
log.Printf("signed-url persist failed key=%s token=%s", key, raw)
```

`raw` 是完整签名。SEV-1 窗口里的审计已经证明链接可被二次使用；再把 token 打进日志等于把私有文件钥匙写进可检索文本。改为 `sig` 前 8 位，或只打 `key`。

### 6.4 主要：没有 `expire-mismatch` 指标

修复让单次写入变对，但名义 TTL 与 Redis `TTL` 再漂一个数量级时仍然静默。本事故的检测失败已经演示过这一点。`PR #1843` 至少要留一次对比采样，差 ≥10× 告警。可以是很小的 gauge，但不能不做。允许合入后补，必须作为结构动作项跟踪，直到预发打过一次真阳性。

### 6.5 次要

- `ttl_ms` 在注释里仍写成「毫秒整数，传给 Expire 时乘 Second」——那是旧 bug 的句子，会误导下一轮评审。改注释。
- `session_test.go` 的测试名 `TestExpireCalled` 已过时，应改成量级断言的名字。
- 魔法数 `90_000` 建议变成具名常量 `defaultSignatureTTL`。

## 7. 测试覆盖

| 场景 | 现状 | 合入前 |
|------|------|--------|
| `ttl_ms` 乘 `Millisecond` | 有，断言 duration == 90s | 保留 |
| `ttl_ms <= 0` 拒绝 | 无 | 阻断，必须有 |
| 跨日 23:59 / 00:01 | 无 | 主要，24h 内可补但须登记 |
| mock 只数调用次数 | 旧测试仍在 | 删掉或改成量级断言 |
| 日志不含完整 token | 无 | 主要，与 6.3 一起 |
| `expire-mismatch` 真阳性 | 无 | 结构项，预发打一次 |

集成测试不要再用 90ms 轮询假装等到过期。最短可用办法：把测试 TTL 降到 2s，断言键消失；生产路径仍走 90s 常量。

## 8. 动作项

| 优先级 | 项 | 负责人向 | 状态 |
|--------|----|----------|------|
| 立即 | 热修复已上线；确认无残留 `TTL > 120` 的 `sig:*` | 值班 | 20:40 完成 |
| 立即 | `ttl_ms <= 0` 拒绝并补测试 | 认证 | 合入前 |
| 短期 | 给 `Expire` mock 增加 duration 量级断言；补跨日边界测试 | 认证 | 合入后 24h |
| 短期 | 日志去掉完整 token；只保留 `sig` 前 8 位 | 认证 | 合入后 24h |
| 结构 | 增加 `expire-mismatch` 指标：名义 TTL 与 Redis TTL 相差 ≥10× 则告警 | 可观测 | 预发真阳性前保持 SEV-1 结构债 |
| 结构 | 全库检索 `ttl_ms * time.Second` | 认证 | 不在热修复范围 |

## 9. 残留风险与未决项

| 风险 | 是否被热修复关闭 | 说明 |
|------|------------------|------|
| 已吊销 `signed-url` 仍可下载 | 是，热路径 | 依赖缓解脚本已跑完 |
| 零 / 负 TTL 写入 Redis | 否 | 阻断项，合入前必须关 |
| 其他模块仍按秒乘 `ttl_ms` | 否 | 全库检索是结构动作项 |
| 跨日墙钟与 Redis TTL 漂移 | 否 | 见 6.2 |
| 日志泄露 token | 否 | 见 6.3 |
| 名义 TTL 与实际 TTL 再漂数量级 | 否 | 见 6.4，SEV-1 结构债仍在 |

未决：

- 37 条二次使用是否构成对外通知，法务未决。本复盘不代替通知决策。
- `sin-1` 尚未接到 2.14.0，保持冻结到 `expire-mismatch` 在预发打过真阳性。
- 合入后仍按 SEV-1 跟踪结构债，直到 `expire-mismatch` 告警在预发打过一次真阳性。
