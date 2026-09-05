# Example: checkout（最小）

Date: 2026-09-05
Skill: project-spec-mirror

下面两段是交卷级最小示例，不要再加文件表或函数走读。

## briefing/overview.md（摘）

```markdown
# example-api

给店铺用的下单 API。

## 背景与目标

- 谁用：店铺后台
- 目标：创建订单并扣减库存
- 非目标：支付渠道对接

## 主处理线

1. [下单](flows/checkout.md)
```

## briefing/flows/checkout.md（摘）

```markdown
# 下单

买家提交商品与数量。成功则库存减少并生成订单号；库存不足则失败且不扣款。
```

## agent/specs/checkout/spec.md

```markdown
# checkout

## Purpose
创建订单并扣减库存。

## Requirements

### Requirement: 库存不足时不创建订单
系统 SHALL 拒绝该订单且不扣款。

#### Scenario: 库存为 0
- **WHEN** 请求数量大于可用库存
- **THEN** 订单不创建
- **THEN** 账户余额不变
```

## evidence/source-map.md（摘）

```markdown
| 能力 | 源路径 | spec |
|------|--------|------|
| checkout | `internal/order` | [checkout](../agent/specs/checkout/spec.md) |
```
