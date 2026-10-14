# 后端 · 个人记账本（FastAPI + SQLAlchemy + MySQL）

## 一、依赖环境

| 组件 | 版本要求 | 说明 |
|---|---|---|
| Python | 3.11+（开发验证用 3.12.14） | |
| MySQL | 8.0（5.7 亦可） | 需要真实数据库，不使用内存库 |
| 驱动 | PyMySQL + cryptography | MySQL 8 默认 `caching_sha2_password`，必须装 `cryptography` |

## 二、初始化步骤（从零到能跑）

> 图省事的话，直接双击 `backend\start.bat`：它会自动检查虚拟环境、初始化数据库、启动服务。
> 想停服就按 `Ctrl+C`，或在 PowerShell 里执行 `.\stop.ps1`。

### 1. 安装依赖

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1        # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
```

### 2. 配置环境变量

```powershell
copy .env.example .env              # macOS/Linux: cp .env.example .env
```

打开 `.env`，**至少**改这三项：

```ini
DB_PASSWORD=你的 MySQL 密码
DB_NAME=ledger
JWT_SECRET_KEY=换成随机长字符串
```

生成随机密钥：

```powershell
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

> `.env` 已在 `.gitignore` 中，不会被提交；密码、密钥一律不硬编码在代码里。

### 3. 初始化数据库（二选一）

**方式 A：执行 SQL 脚本（推荐，和 QA 环境一致）**

```powershell
# PowerShell 不支持 < 重定向，用 cmd /c 包一层
cmd /c "mysql -u root -p --default-character-set=utf8mb4 < sql\01_schema.sql"
cmd /c "mysql -u root -p --default-character-set=utf8mb4 < sql\02_seed.sql"
```

```bash
# macOS / Linux / Git Bash
mysql -u root -p --default-character-set=utf8mb4 < sql/01_schema.sql
mysql -u root -p --default-character-set=utf8mb4 < sql/02_seed.sql
```

**方式 B：用 Python 脚本自动建库建表 + 灌预置分类（幂等，可重复执行）**

```powershell
python -m app.db.init_db              # 建库 + 建表 + 15 个预置分类
python -m app.db.init_db --with-demo  # 额外创建演示账号 demo / Demo1234
```

脚本做了三件事：`CREATE DATABASE IF NOT EXISTS` → `Base.metadata.create_all`（按 ORM 建模建表）→ 灌预置分类；失败会打印完整堆栈并以退出码 1 结束。

### 4. 启动服务

```powershell
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

| 入口 | 地址 |
|---|---|
| 前端页面 | http://localhost:8000/ |
| Swagger UI | http://localhost:8000/docs |
| OpenAPI JSON（导入 Apifox） | http://localhost:8000/openapi.json |
| 健康检查 | http://localhost:8000/api/v1/health |

## 三、目录结构

```
backend/
├── app/
│   ├── main.py                 # 应用入口：中间件、路由、异常处理、静态资源挂载
│   ├── core/
│   │   ├── config.py           # pydantic-settings 读取 .env
│   │   ├── security.py         # bcrypt 哈希 + JWT 签发/校验
│   │   ├── logging_config.py   # 标准 logging：控制台 + 按天轮转文件
│   │   ├── exceptions.py       # BizError + 全局异常处理器（统一响应体）
│   │   └── validators.py       # 业务层校验：密码策略、金额规则
│   ├── db/
│   │   ├── base.py             # Declarative Base + 时间戳 Mixin
│   │   ├── session.py          # engine / SessionLocal / get_db
│   │   ├── seed_data.py        # 预置分类与演示账号定义
│   │   └── init_db.py          # 建库建表 + 灌初始数据（可执行脚本）
│   ├── models/                 # SQLAlchemy 模型：user / category / transaction
│   ├── schemas/                # Pydantic 模型：common / user / category / transaction
│   ├── crud/                   # 数据访问层
│   ├── api/
│   │   ├── deps.py             # get_db / get_current_user
│   │   └── v1/                 # auth / category / transaction / health / router
│   └── middleware/
│       └── request_log.py      # 请求日志 + request_id
├── sql/
│   ├── 01_schema.sql           # 建库建表 DDL
│   └── 02_seed.sql             # 预置分类 + 演示账号
├── scripts/
│   └── smoke_test.py           # 针对运行中服务的冒烟测试（真实 HTTP）
├── tests/                      # pytest 回归用例（86 条）
├── logs/                       # 运行时生成：app.log / error.log
├── .env.example                # 环境变量模板
├── ruff.toml                   # 代码规范配置
└── requirements.txt
```

## 四、日志

| 文件 | 内容 |
|---|---|
| `logs/app.log` | 全部日志（请求日志、业务日志、错误） |
| `logs/error.log` | 仅 ERROR 及以上，含完整堆栈 |

日志格式：

```
2026-10-14 20:51:49 | WARNING  | rid=b5614f12c4e2 | app.core.exceptions | 业务异常 | GET /api/v1/transactions/1 | status=404 | 记录不存在或已被删除
2026-10-14 20:51:49 | WARNING  | rid=b5614f12c4e2 | app.request | 请求完成 | GET /api/v1/transactions/1 | status=404 | 4.1ms | client=127.0.0.1
```

- `rid` 就是响应头 `X-Request-ID`，**一次请求的所有日志行 rid 相同**，排查时直接搜这个值。
- 文件按天轮转，保留 `LOG_RETENTION_DAYS`（默认 7）份。
- 出于安全考虑，**日志不记录请求体**（避免明文密码落盘）。

## 五、测试

```powershell
pytest -q                                   # 86 条用例，用 SQLite 内存库，不需要 MySQL
python scripts\smoke_test.py                # 对运行中的服务发真实 HTTP 请求（37 项断言）
ruff check app tests scripts                # 代码规范检查
ruff check app tests scripts --fix           # 自动修复 import 顺序等问题
```

## 六、常见问题

| 现象 | 原因与处理 |
|---|---|
| `Access denied for user 'root'@'localhost'` | `.env` 里 `DB_PASSWORD` 不对，或 MySQL 未启动（`net start MYSQL80`） |
| `RuntimeError: cryptography is required` | `pip install cryptography`（MySQL 8 认证插件需要） |
| 启动日志出现「数据库连接失败，请检查 backend/.env」 | 服务仍会启动（方便先调接口），但所有读写都会失败；按上一行排查 |
| PowerShell 执行 `mysql ... < sql\file.sql` 报语法错误 | PowerShell 不支持 `<` 重定向，按上面用 `cmd /c "..."` 包一层 |
| 前端页面白屏，提示「前端资源加载失败」 | CDN（unpkg.com）不可达；把 `vue.global.prod.js` 下载到 `frontend/static/js/` 并改本地引用 |
| 端口 8000 被占用 | `uvicorn app.main:app --reload --port 8001`，端口变了前端页面同源访问也会跟着变（同源部署） |
| 中文日志在控制台显示乱码 | 控制台代码页与日志编码不一致，`logs/app.log` 本身是 UTF-8，用编辑器打开正常 |

## 七、代码规范

- Python：PEP8（`ruff.toml` 配置 `line-length=110`，`ruff check` 零告警）。
- 提交信息：Conventional Commits，例如 `feat: 新增收支记录列表接口`、`fix: 修复金额为 0 时未拦截的问题`。
