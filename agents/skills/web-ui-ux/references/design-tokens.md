# 设计 token 与响应式 / 可访问性默认值

项目已有设计系统时以项目为准；没有时提议这套最小 token 集，不引入大库。

## 间距（4/8 倍数：4, 8, 12, 16, 24, 32, 48, 64）

```css
--space-1: 4px;  --space-2: 8px;  --space-3: 12px; --space-4: 16px;
--space-5: 24px; --space-6: 32px; --space-7: 48px; --space-8: 64px;
```

## 字号（12 / 14 / 16 / 18 / 20 / 24 / 32 / 40）

```css
--text-xs: 12px; --text-sm: 14px; --text-base: 16px; --text-lg: 18px;
--text-xl: 20px; --text-2xl: 24px; --text-3xl: 32px; --text-4xl: 40px;
```

正文 16px、行高 1.5；长文本行宽控制在 60-75 字符。

## 颜色（必须用语义化 token，不用裸色值）

```css
--color-bg  --color-surface  --color-surface-hover  --color-border
--color-text  --color-text-muted  --color-primary  --color-primary-hover
--color-danger  --color-success  --color-warning
```

不用颜色作为唯一状态提示，必须配合图标或文字。

## 圆角 / 阴影 / 动效 / z-index

```css
--radius-sm: 6px; --radius-md: 10px; --radius-lg: 16px; --radius-full: 9999px;
--shadow-sm / --shadow-md / --shadow-lg   /* 只用这 3 级 */
--duration-fast: 150ms; --duration-normal: 250ms;
--ease-out: cubic-bezier(0.16, 1, 0.3, 1);
--z-dropdown: 1000; --z-modal: 2000; --z-toast: 3000;
```

尊重 `prefers-reduced-motion`。

## 响应式规则

- mobile-first；断点 640 / 768 / 1024 / 1280；优先 flex/grid，少用媒体查询。
- 移动端触控目标 ≥44x44px；不允许横向滚动。
- 长文本、超长邮箱、中英混排不撑破布局：图片 `max-width: 100%`，长文本容器 `min-width: 0`，溢出用 `overflow-wrap: anywhere` 或 `text-overflow`。

## 可访问性规则

- 语义化标签：header / nav / main / section / button / form / label。
- 图片有 alt（装饰图 `alt=""`）；图标按钮有 `aria-label`。
- 表单 label 必须可见，placeholder 不替代 label；错误用 `aria-describedby` 且字段标 `aria-invalid`。
- 键盘可操作：Tab 顺序合理、焦点不丢失；模态框焦点锁定、Esc 关闭。
- 正文对比度 ≥4.5:1，大字 ≥3:1；不用 div 当按钮；不用颜色作为唯一状态提示。

## 内容与边界

真实文案，不用 Lorem Ipsum。边界数据：空、超长、特殊字符、中英混排、emoji；数字、金额、日期、手机号格式统一。项目有 i18n 时不硬编码文案。
