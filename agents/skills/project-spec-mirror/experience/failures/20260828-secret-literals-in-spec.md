# 源码密钥字面量被抄进镜像

- Date: 2026-08-28
- Kind: failure
- Skill: project-spec-mirror
- Status: current
- Context: 整理能力或源映射时，源码常量含 AppKey / SecretKey 一类凭据

## What happened

Agent 把鉴权常量的赋值写进说明文字，镜像因此带上密钥原文。

## Lesson

- 凭据只写字段名与注入方式，值一律 `<REDACTED>`；产品标识不是密钥。
- 可复用于后续 build/update。
