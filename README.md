# 个人记账本

一个前后端分离的轻量记账系统：注册登录 → 记录日常收支 → 查看明细与汇总。

后端 FastAPI + SQLAlchemy + MySQL（真实数据库连接），前端 Vue 3（CDN 引入，无需 npm 构建），同源部署，一个端口跑完整个应用。

## 功能清单

| 模块 | 能力 |
|---|---|
| 用户 | 注册（用户名 3-20 位）、登录（JWT，有效期 2 小时）、获取当前用户 |
| 分类 | 15 个系统预置分类（餐饮/交通/工资…）+ 用户自定义分类的增删改 |
| 记账 | 新增收支（类型/金额/分类/备注/日期）、详情、部分更新、软删除 |
| 查询 | 明细列表（分页 + 类型/分类/日期区间/备注关键字筛选 + 排序）、收支汇总（总收入/总支出/结余） |
| 工程 | 统一响应体与错误码、全局异常处理、请求日志与 request_id、bcrypt 密码哈希、`ruff` 规范零告警 |

## 快速开始

```powershell
# 1. 后端依赖
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# 2. 配置（改 DB_PASSWORD 与 JWT_SECRET_KEY）
copy .env.example .env

# 3. 建库 + 建表 + 预置分类 + 演示账号
python -m app.db.init_db --with-demo

# 4. 启动
uvicorn app.main:app --reload --port 8000
```

打开 http://localhost:8000/ ，用 `demo / Demo1234` 登录即可。

> 也可以按 `backend/sql/01_schema.sql`、`backend/sql/02_seed.sql` 手工初始化，和 QA 环境完全一致。

## 完整目录结构

```
acjl/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                    # 应用入口（中间件 / 路由 / 异常处理 / 静态资源）
│   │   ├── core/
│   │   │   ├── config.py              # .env 配置加载（数据库密码、JWT 密钥外置）
│   │   │   ├── security.py            # bcrypt 加盐哈希 + JWT 签发校验
│   │   │   ├── logging_config.py      # 标准 logging（控制台 + 按天轮转文件）
│   │   │   ├── exceptions.py          # BizError + 全局异常处理器
│   │   │   └── validators.py          # 密码策略 / 金额规则（业务层强制校验）
│   │   ├── db/
│   │   │   ├── base.py                # Declarative Base + 时间戳 Mixin
│   │   │   ├── session.py             # engine / SessionLocal / get_db
│   │   │   ├── seed_data.py           # 预置分类、演示账号
│   │   │   └── init_db.py             # 建库建表 + 灌初始数据
│   │   ├── models/
│   │   │   ├── user.py
│   │   │   ├── category.py
│   │   │   ├── transaction.py
│   │   │   └── enums.py
│   │   ├── schemas/                   # Pydantic 请求/响应模型
│   │   │   ├── common.py              # 统一响应体、分页
│   │   │   ├── user.py
│   │   │   ├── category.py
│   │   │   └── transaction.py
│   │   ├── crud/                      # 数据访问层
│   │   │   ├── user.py
│   │   │   ├── category.py
│   │   │   └── transaction.py
│   │   ├── api/
│   │   │   ├── deps.py                # get_db / get_current_user
│   │   │   └── v1/
│   │   │       ├── router.py
│   │   │       ├── auth.py
│   │   │       ├── category.py
│   │   │       ├── transaction.py
│   │   │       └── health.py
│   │   └── middleware/
│   │       └── request_log.py         # 请求日志 + X-Request-ID
│   ├── sql/
│   │   ├── 01_schema.sql              # 建库建表 DDL（含索引/外键/CHECK 约束）
│   │   └── 02_seed.sql                # 预置分类 + 演示账号
│   ├── scripts/
│   │   └── smoke_test.py              # 对运行中的服务发真实 HTTP 的冒烟测试
│   ├── tests/
│   │   ├── conftest.py
│   │   ├── test_auth.py
│   │   ├── test_categories.py
│   │   ├── test_transactions.py
│   │   └── test_validation_matrix.py  # 与校验矩阵逐行对应的绕过前端用例
│   ├── logs/                          # 运行时生成（已 gitignore）
│   ├── .env.example
│   ├── .gitignore
│   ├── ruff.toml
│   ├── requirements.txt
│   └── README.md                      # 后端启动 / 数据库初始化 / 排错
├── frontend/
│   ├── index.html                     # 记账主页（汇总卡片 / 筛选 / 明细表 / 弹窗表单）
│   ├── login.html                     # 登录注册页
│   └── static/
│       ├── css/style.css
│       └── js/
│           ├── api.js                 # 接口封装（注入 Token、401 跳转、422 明细拼接）
│           ├── validate.js            # 前端体验层校验规则
│           ├── login.js
│           ├── app.js
│           └── vendor-check.js        # CDN 不可达时的友好提示
├── docs/
│   ├── API.md                         # 接口文档（可直接导入 Apifox）
│   └── VALIDATION-MATRIX.md           # 校验责任矩阵（前端做了什么 / 后端也做了什么）
└── README.md
```

## 文档导航

| 文档 | 用途 |
|---|---|
| [docs/API.md](docs/API.md) | 全部接口的方法、URL、请求头、参数表、请求/响应示例、错误码清单、Apifox 导入步骤 |
| [docs/VALIDATION-MATRIX.md](docs/VALIDATION-MATRIX.md) | 38 个校验点的前端/后端分工对照表 + 可直接照抄的 Postman 用例 |
| [backend/README.md](backend/README.md) | 环境准备、数据库初始化、启动命令、日志说明、常见问题与修复命令 |

## 校验分工（一页速查）

完整矩阵见 [docs/VALIDATION-MATRIX.md](docs/VALIDATION-MATRIX.md)，记忆规则只有两条：

1. **前端做校验只是为了体验**：不通过就弹窗，不发请求（`frontend/static/js/validate.js`）。
2. **后端一定会独立再校验一遍**：类型/结构/格式问题返回 **422** + 字段级 `errors[]`；密码策略、金额规则等业务与安全问题返回 **400/401/403/404/409**。

因此用 Postman 绕过前端直接调用：

- `password: "123456"` → **400** `密码长度必须为 8-20 位`
- `amount: "-100"` / `amount: "0"` → **400** `金额必须大于 0`
- `amount: "abc"` → **422**，`errors[0].field = "body.amount"`

## 数据库

三张表：`users`、`categories`、`transactions`。关键设计：

- 金额 `DECIMAL(12,2)` 恒为正数，方向由 `type` 决定；库层面带 `CHECK (amount > 0)`；
- 密码只存 bcrypt 哈希（cost=12），接口响应永不返回密码相关字段；
- `transactions` 的索引全部以 `user_id` 打头，保证"查自己的账"走索引；
- `categories.user_id = NULL` 表示系统预置分类，所有用户可见且不可删改；
- 记账记录采用**软删除**（`is_deleted`），删除后各查询立即不可见，数据仍可追溯。

建库建表 SQL 见 [backend/sql/01_schema.sql](backend/sql/01_schema.sql)，初始数据见 [backend/sql/02_seed.sql](backend/sql/02_seed.sql)。

## 质量状态

| 检查项 | 结果 |
|---|---|
| `pytest -q` | 86 条用例全部通过 |
| `scripts/smoke_test.py`（真实 MySQL + 真实 HTTP） | 37 项断言全部通过 |
| `ruff check app tests scripts` | 全部通过，零告警 |
| MySQL 8.0.42 实测 | 建库建表、索引、外键、CHECK 约束、emoji/中文存储均正常 |

## Git 提交建议（Conventional Commits）

代码已按模块拆分，建议按下面顺序分次提交（由你执行）：

```
chore: 初始化项目结构与工程配置
feat: 集成日志系统与全局异常处理
feat: 定义用户分类收支模型与建表脚本
feat: 实现用户注册登录与 JWT 鉴权
feat: 实现密码强度校验与 bcrypt 加盐存储
feat: 实现分类管理接口
feat: 实现收支记录增删改查与汇总接口
feat: 添加数据库初始化脚本与预置分类
feat(frontend): 实现登录注册页面
feat(frontend): 实现记账主页（汇总/筛选/明细/新增弹窗）
test: 补充 86 条接口回归用例与冒烟测试脚本
docs: 补充接口文档与校验责任矩阵
```
