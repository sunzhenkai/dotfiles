# Python API

本 reference 只在栈为 `python-api` 时读取。分层与建议以 `SKILL.md` Python 表为准；这里只写怎么落地。先选层并得到用户确认的最终方案，再执行**与所选 Web Framework 匹配**的路径，不要把所有备选都装上。

**工具命令优先**：项目骨架用 `uv init`、`uv add`、`django-admin startproject` 等官方命令生成。官方 CLI 可用时不要从零手搓 `pyproject.toml` 与完整目录树。CLI 缺失时先按 `SKILL.md` 询问是否补齐。

## 建议 → init 行为

| 建议 | init | align 缺口 |
|------|------|------------|
| 必选 | 必须具备，缺则不算完成 | 列为应补 |
| 默认 | 未指定替代时采用 | 已用等价替代则记录偏差，不强制改回 |
| 推荐 | 默认装入；用户明确拒绝才省略 | 列为建议补，确认后再改 |
| 需要…再用 | **不预装** | 仅当需求已出现、或用户要求时才提议 |
| 特定场景再用 | **不作为默认**；仅需求匹配或用户点名 | 已采用则按该路径对照，不改回默认 |
| 用户点名 | **不预装**；仅用户点名该库 | 已采用则按该库对照，不改回默认 |

## 需求 → 选层

| 已确认需求 | 选择 |
|------------|------|
| 用户点名 FastAPI / Django / Flask / Litestar | 用用户的 Web Framework |
| 要 Django Admin、MTV、Django 生态插件或传统全栈 Django | Django |
| 其余纯 HTTP API，或需求未区分框架 | FastAPI |
| 非 Django 的 API / Validation | Pydantic + OpenAPI（FastAPI / Litestar 原生导出；Flask 用 Pydantic 模型并显式提供 OpenAPI 或等价 schema） |
| Django 路径的 API | django-rest-framework；不要为了「看起来像 FastAPI」再叠一套 Pydantic 除非用户点名 |
| ORM（非 Django） | SQLAlchemy |
| ORM（Django） | Django ORM |
| 要模型类与 Pydantic schema 同一套，或点名 SQLModel | SQLModel（不要与手写 SQLAlchemy 模型双轨） |
| 点名 Tortoise ORM | Tortoise（不要与 SQLAlchemy 双轨） |
| 要后台任务 | **只选一个**：Celery（多 worker / Beat / 已有该生态）、Dramatiq（更简单 broker 模型）、ARQ（已是 asyncio + Redis） |
| 同时提到多种 jobs 且未选 | 问一句，不要三个都装 |
| 测试 | pytest + httpx 必选 |
| 要浏览器 E2E | Playwright；API-only 不预装 |
| Tooling | uv 默认；Ruff 与 pyright（或用户指定的 mypy）推荐装入 |

Async / Runtime：FastAPI / Litestar 用 asyncio + uvicorn；anyio 随框架传递，不要单独钉版本。Django 用其官方 ASGI/WSGI，不要无故改成 uvicorn 优先。

## 共用（所有 python-api 路径）

优先 `uv`：

```bash
uv init --name <project-name>
```

无 `uv` 时：不要直接改用 venv。把 `uv` 列为缺失依赖，**询问是否补齐**（安装 `uv`，或改用 `python3 -m venv .venv` + pip）。未确认不得自行切换。不要全局 `pip install`。

`uv init` 若写出与所选框架无关的占位 `main.py`，删除该占位，避免两个入口并存。

随后按所选路径 `uv add` 依赖；共用开发依赖：

```bash
uv add --dev pytest httpx ruff pyright
```

用户明确只要 mypy、不要 pyright 时，把 `pyright` 换成 `mypy`。用户明确拒绝推荐工具时省略 Ruff / 类型检查。

`.gitignore` 至少覆盖：`.venv/`、`__pycache__/`、`*.py[cod]`、`.env`、`.ruff_cache/`、`.pytest_cache/`、`.mypy_cache/`。Django 路径另加 `db.sqlite3`、`staticfiles/`；SQLAlchemy 路径另加 `*.db`。

README 写清：安装依赖、启动、health URL、`pytest`、Ruff（若已装）。不要写虚构的部署/公司环境。

## FastAPI（默认）

优先 `uv init` + `uv add`。FastAPI 无独立 create 模板时，用上述工具命令生成项目后再写入本约定的最小包结构，不要从零手搓依赖清单。不要手搓与 FastAPI 文档漂移的大型目录（无 `services/` 领域分层，除非用户要求）。

```bash
uv add "fastapi[standard]" sqlalchemy pydantic-settings
```

`fastapi[standard]` 含 uvicorn；不要再重复加一份冲突的 ASGI 服务器，除非用户点名。

### 目录约定

```text
<project-root>/
  pyproject.toml
  README.md
  .gitignore
  .env.example
  app/
    __init__.py
    main.py              # FastAPI()；挂路由；可供 uvicorn / fastapi dev
    api/
      __init__.py
      health.py          # GET /api/health
    core/
      __init__.py
      config.py          # pydantic-settings
      db.py              # SQLAlchemy engine / Session；health 不得依赖 DB
    models/
      __init__.py        # 只导出 Base；不放业务表
    schemas/
      __init__.py
      health.py          # Pydantic；与 health 响应一致
  tests/
    test_health.py
```

`app/main.py` 必须能被 OpenAPI 发现（默认 `/docs`、`/openapi.json`）。不要关 OpenAPI。不要加用户系统、鉴权或示例 CRUD。

`config.py`：`SECRET_KEY` / `DEBUG` / `DATABASE_URL` 从环境变量读取；本地缺省仅用于开发，注释标明不可用于生产。

`.env.example`：

```text
APP_SECRET_KEY=dev-only-change-me
APP_DEBUG=true
DATABASE_URL=sqlite:///./app.db
```

仅当本次同时初始化会跨域访问本 API 的前端时，才配置 CORS；API-only 不要默认加 CORS。

不要默认装 Alembic；有真实迁移需求再加。不要默认装 SQLModel、Tortoise、Celery、Dramatiq、ARQ、Playwright。

### 冒烟（init 必做）

```bash
uv run pytest
uv run ruff check .
```

无 `uv` 则用 `.venv/bin/pytest` 与 `.venv/bin/ruff`。`tests/test_health.py` 用 httpx / FastAPI `TestClient` 断言 `GET /api/health` 返回 JSON `{"status": "ok"}`。失败则修复脚手架后再结束。不要启动长期 `uvicorn` / `fastapi dev`。

## Django（特定场景）

仅当选层结果为 Django 时执行本节。默认：**Django + django-rest-framework** + Django ORM。

```bash
uv add django djangorestframework
uv run django-admin startproject config .
```

无 `uv` 时：

```bash
.venv/bin/pip install django djangorestframework
.venv/bin/django-admin startproject config .
```

- Django 工程包名默认 `config`（避免与目录名撞车）。用户指定其他包名则用用户的。
- 在目标根执行 `startproject`，使 `manage.py` 位于项目根。

### 目录约定

```text
<project-root>/
  pyproject.toml          # 或 requirements.txt（仅无 uv 时）
  manage.py
  README.md
  .gitignore
  .env.example
  config/
    __init__.py
    settings.py
    urls.py
    wsgi.py
    asgi.py
    views.py              # 仅 health
  apps/
    __init__.py           # 业务 app 放这里；init 不创建业务 app
  tests/
    test_health.py
```

后续业务 app：`uv run python manage.py startapp <name> apps/<name>`，`INSTALLED_APPS` 登记 `apps.<name>`。init 阶段不要 `startapp` 业务应用。

### 必须写入的配置

在 `config/settings.py`（官方生成后再改，不要整文件替换掉未知项）：

- `INSTALLED_APPS` 加入 `rest_framework`。
- `SECRET_KEY` / `DEBUG` / `ALLOWED_HOSTS` 从环境变量读取；本地缺省仅用于开发（与 `.env.example` 一致），注释标明不可用于生产。
- 增加：

```python
REST_FRAMEWORK = {
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
    ],
    "DEFAULT_PARSER_CLASSES": [
        "rest_framework.parsers.JSONParser",
    ],
}
```

- 仅当本次同时初始化会跨域访问本 API 的前端时，才添加 `django-cors-headers` 并配置 `CORS_ALLOWED_ORIGINS`；API-only 不要默认加 CORS。

`config/views.py` + `config/urls.py` 提供 `GET /api/health/`，JSON `{"status": "ok"}`。不要加 admin 定制、用户系统、鉴权或示例 CRUD。Admin 场景只保留 `startproject` 自带的 admin，不要在 init 里做定制站点。

开发依赖另加 `pytest-django`。在 `pyproject.toml` 或 `pytest.ini` 设置 `DJANGO_SETTINGS_MODULE=config.settings`。

`.env.example`：

```text
DJANGO_SECRET_KEY=dev-only-change-me
DJANGO_DEBUG=true
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1
```

README 写清：安装依赖、`migrate`（init 可跑 `migrate` 以创建本地 sqlite）、`runserver`、health URL、`pytest`。

### 冒烟（init 必做）

```bash
uv run python manage.py check
uv run python manage.py migrate --noinput
uv run pytest
uv run ruff check .
```

无 `uv` 则用 `.venv/bin/python` 与对应工具。不要 `runserver`。任一步失败则修复脚手架后再结束。

## Flask（用户点名）

仅用户点名 Flask 时：

```bash
uv add flask sqlalchemy pydantic pydantic-settings
```

最小可运行应用（`app/main.py` 或根 `app.py`，二选一、保持扁）：提供 `GET /api/health` 与 Pydantic 响应模型。用 SQLAlchemy 与 pydantic-settings，规则同 FastAPI：health 不依赖 DB。不要发明深度分层。冒烟：`pytest` + `ruff check`（httpx 测 health）。不要默认加 Flask-RESTX / 蓝图全家桶，除非用户要求。

## Litestar（用户点名）

仅用户点名 Litestar 时：

```bash
uv add "litestar[standard]" sqlalchemy pydantic-settings
```

若 extra 名称与当时官方文档不一致，改用文档中的等价安装方式，并显式加上 uvicorn。最小应用提供 `GET /api/health`、Pydantic schema、原生 OpenAPI。SQLAlchemy session 骨架同 FastAPI 原则。冒烟：`pytest` + `ruff check`。不要启动长期 uvicorn。

## 可选层（按需，不预装）

只在选层结果需要时加**一个**对应实现；加完后补一条不访问外部 broker / 浏览器的单测或跳过说明。

| 层 | 落地 |
|----|------|
| SQLModel | 用 SQLModel 代替手写 `DeclarativeBase` 模型；Pydantic schema 与表定义合一。不要同时维护两套模型。 |
| Tortoise ORM | 按官方 FastAPI/Litestar 集成初始化；不要与 SQLAlchemy 并存。 |
| Celery | 官方入口创建最小 `tasks` 模块 + 配置从环境变量读 broker；init 不写 docker-compose，不连真实 broker。 |
| Dramatiq | 同上，只建最小 actor 模块。 |
| ARQ | 仅 asyncio 路径；最小 worker 设置从环境变量读 Redis URL。 |
| Playwright | `pytest-playwright` 或官方 Python Playwright；一条访问文档或 health 页的 smoke。init **不**默认下载浏览器；README 写明 `playwright install`。 |

## align 对照

按**当前项目已采用的 Web Framework**对照，不要把异栈列为「应改成默认」。缺什么列什么，确认后再补。

### 已是 FastAPI（或用户确认保留的 Litestar / Flask）

| 项 | 期望 |
|----|------|
| 依赖 | 所选框架；Pydantic；非 Django 时 SQLAlchemy（或用户已选的 SQLModel / Tortoise） |
| OpenAPI | FastAPI / Litestar 可导出；Flask 有等价 schema 或显式 OpenAPI |
| health | 有可访问的健康检查，或用户明确不要 |
| 配置 | 密钥与 `DATABASE_URL` 来自环境变量；无明文生产密钥入库 |
| 测试 | pytest 可运行；httpx 覆盖 health |
| Tooling | 已有 Ruff / 类型检查则不换实现；没有则按推荐提议 |
| Jobs / Playwright / SQLModel | 仅当项目已有该需求或用户要加 |

### 已是 Django

| 项 | 期望 |
|----|------|
| 依赖 | `django`、`djangorestframework` |
| `INSTALLED_APPS` | 含 `rest_framework` |
| `REST_FRAMEWORK` | 有显式配置（可与上表不同，但应存在） |
| health | 有可访问的健康检查，或用户明确不要 |
| 业务 app 位置 | 约定在 `apps/`；已有 app 在别处则**不要**搬家，只在摘要说明偏差 |
| ORM | Django ORM；不要擅自换成 SQLAlchemy |
| 密钥 | 无明文生产密钥入库 |
| 测试 | pytest 可运行（pytest-django 或项目已有等价） |

已是未点名且 v1 未覆盖的框架，或 Python 但不是 API：报告「栈不兼容」，给出若迁移需要替换的入口与依赖；**不改代码**，除非用户明确要求迁移并确认计划。
