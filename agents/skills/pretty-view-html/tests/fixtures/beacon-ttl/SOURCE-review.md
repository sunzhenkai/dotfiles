# 灯塔网关 SEV-1 热修复评审：signed-url TTL 单位

这份草稿是 pretty-view-html 阅读页展示测试的修复 code review 源稿。读者对象是将要合入热修复的评审人，不是事故叙事。事故背景见同夹具 `SOURCE-postmortem.md`。产品「灯塔网关（Beacon Gate）」是虚构的个人文件分发网关。

## 结论

范围：PR `#1843`，热修复 `internal/auth/session.go` 中 `ttl_ms` 被当成秒写入 Redis 的问题。结论：**带条件可合入**——阻断项必须先改；主要项可在合入后 24h 内补，但要登记。残留风险不因热修复关闭 SEV-1 的结构债。

## 目录

1. [范围](#1-范围)
2. [阻断](#2-阻断)
3. [主要](#3-主要)
4. [次要](#4-次要)
5. [测试覆盖](#5-测试覆盖)
6. [残留风险](#6-残留风险)

## 1. 范围

审查的是热修复，不是整次 TTL 毫秒化重构。

- 合入目标：让 `signed-url` 的 Redis TTL 回到约 90s。
- 已看文件：`internal/auth/session.go`、`internal/auth/session_test.go`、`internal/auth/redis_expire.go`。
- 未看：网关其他模块是否还有 `ttl_ms * time.Second`；那是复盘动作项，不在本 PR。

当前补丁把 `persistSignature` 改成：

```go
ttl_ms := 90_000
if err := rdb.Expire(ctx, key, time.Duration(ttl_ms)*time.Millisecond).Err(); err != nil {
    return err
}
```

方向正确。下面按严重度分组，每条给路径、证据和建议。

## 2. 阻断

### 2.1 零值与负值仍会写入

`internal/auth/session.go:142` 在换算前没有拒绝非法 `ttl_ms`。测试里用 `ttl_ms := 0` 时，`Expire` 仍被调用。

```go
func persistSignature(ctx context.Context, key string, ttl_ms int64) error {
    return rdb.Expire(ctx, key, time.Duration(ttl_ms)*time.Millisecond).Err()
}
```

Redis 对 0 duration 的行为与「立即过期」并不总一致；负值会变成巨大的 uint 转换风险。热修复必须在调用 `Expire` 前拒绝 `ttl_ms <= 0`，并覆盖该分支。不修则带条件结论不成立。

## 3. 主要

### 3.1 跨日边界没有测试

`internal/auth/session_test.go` 只在同一假时钟下断言 90s。没有覆盖 23:59 → 00:01 的签发与校验。灯塔网关的签名校验用的是墙钟 `expires_at`，TTL 与墙钟任一偏差都会在跨日复现成「链接已过期但 Redis 仍活着」，或反过来。

建议：用固定 `time.Time` 在 `2026-08-12 23:59:30` 签发，拨到次日 00:00:30 再取，断言 Redis TTL 与 `expires_at` 同向收缩。

### 3.2 日志可能带完整 token

`internal/auth/session.go:168` 的失败路径：

```go
log.Printf("signed-url persist failed key=%s token=%s", key, raw)
```

`raw` 是完整签名。SEV-1 窗口里的审计已经证明链接可被二次使用；再把 token 打进日志等于把私有文件钥匙写进可检索文本。改为 `sig` 前 8 位，或只打 `key`。

### 3.3 没有 `expire-mismatch` 指标

修复让单次写入变对，但名义 TTL 与 Redis `TTL` 再漂一个数量级时仍然静默。复盘已把该指标列为结构项；本 PR 至少要留 hook 或 TODO 不够——需要一次对比采样，差 ≥10× 告警。可以是很小的 gauge，但不能不做。

## 4. 次要

- `ttl_ms` 在注释里仍写成「毫秒整数，传给 Expire 时乘 Second」——那是旧 bug 的句子，会误导下一轮评审。改注释。
- `session_test.go` 的测试名 `TestExpireCalled` 已过时，应改成量级断言的名字。
- 魔法数 `90_000` 建议变成具名常量 `defaultSignatureTTL`。

## 5. 测试覆盖

| 场景 | 现状 | 合入前 |
|------|------|--------|
| `ttl_ms` 乘 `Millisecond` | 有，断言 duration == 90s | 保留 |
| `ttl_ms <= 0` 拒绝 | 无 | 阻断，必须有 |
| 跨日 23:59 / 00:01 | 无 | 主要，24h 内可补但须登记 |
| mock 只数调用次数 | 旧测试仍在 | 删掉或改成量级断言 |
| 日志不含完整 token | 无 | 主要，与 3.2 一起 |

## 6. 残留风险

| 风险 | 是否被本 PR 关闭 | 说明 |
|------|------------------|------|
| 已吊销 `signed-url` 仍可下载 | 是，热路径 | 依赖缓解脚本已跑完 |
| 其他模块仍按秒乘 `ttl_ms` | 否 | 全库检索是复盘动作项 |
| 跨日墙钟与 Redis TTL 漂移 | 否 | 见 3.1 |
| 日志泄露 token | 否 | 见 3.2 |
| 名义 TTL 与实际 TTL 再漂数量级 | 否 | 见 3.3，SEV-1 结构债仍在 |

合入后仍按 SEV-1 跟踪结构债，直到 `expire-mismatch` 告警在预发打过一次真阳性。
