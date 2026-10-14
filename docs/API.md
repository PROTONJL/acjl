# 个人记账本 · 接口文档

> 适配 Apifox / Postman。也可以直接把 `http://localhost:8000/openapi.json` 导入 Apifox 自动生成接口集合。

## 一、通用约定

| 项目 | 说明 |
|---|---|
| Base URL | `http://localhost:8000/api/v1` |
| 数据格式 | `Content-Type: application/json; charset=utf-8` |
| 鉴权方式 | 请求头 `Authorization: Bearer <access_token>`（除注册/登录/健康检查外全部需要） |
| 时间字段 | 统一为**服务器本地时间**，格式 `YYYY-MM-DDTHH:mm:ss`（无时区后缀） |
| 日期字段 | `YYYY-MM-DD` |
| 金额字段 | 入参接受数字或字符串；**出参统一为两位小数的字符串**（如 `"25.80"`），避免 JS 浮点精度问题 |
| 请求追踪 | 每个响应都带 `X-Request-ID` 头，和 `backend/logs/app.log` 中的 `rid=` 一一对应 |

### 1.1 统一响应结构

成功：

```json
{ "code": 200, "message": "success", "data": { } }
```

失败（`code` 与 HTTP 状态码一致）：

```json
{ "code": 400, "message": "金额必须大于 0", "data": null }
```

参数校验失败（422）额外返回字段级明细，方便定位：

```json
{
  "code": 422,
  "message": "请求参数校验失败",
  "data": null,
  "errors": [
    {
      "field": "body.amount",
      "message": "Input should be a valid decimal",
      "type": "decimal_parsing",
      "input": "abc"
    }
  ]
}
```

`field` 前缀含义：`body.*` = 请求体字段，`query.*` = Query String 参数。

### 1.2 全局错误码

| HTTP | code | 触发场景 | 响应 `message` 示例 |
|---|---|---|---|
| 200 | 200 | 请求成功 | `success` |
| 201 | 201 | 创建成功（注册、新增分类、新增记录） | `注册成功` / `创建成功` |
| 204 | 204 | 删除成功（**响应体为空**） | — |
| 400 | 400 | 业务规则不满足：密码策略、金额 ≤ 0、金额超两位小数、分类不存在、分类与收支类型不匹配、分类仍被记录占用、开始日期晚于结束日期 | `密码长度必须为 8-20 位` |
| 401 | 401 | 未携带 Token / Token 非法或过期 / 用户名密码错误 | `缺少访问令牌，请先登录` |
| 403 | 403 | 修改或删除系统预置分类 / 账号被停用 | `系统预置分类不允许删除` |
| 404 | 404 | 资源不存在、已被软删除、或不属于当前用户 | `记录不存在或已被删除` |
| 409 | 409 | 用户名已存在 / 邮箱已注册 / 分类重名 | `用户名已存在，请更换后重试` |
| 422 | 422 | 类型、必填、格式、枚举、超出字段精度等**结构性问题** | `请求参数校验失败` + `errors[]` |
| 500 | 500 | 服务端异常（堆栈写入 `error.log`） | `服务器内部错误` |

### 1.3 分页数据格式

列表类接口的 `data` 结构固定为：

```json
{
  "items": [],
  "total": 42,
  "page": 1,
  "page_size": 20,
  "pages": 3
}
```

---

## 二、认证

### 2.1 用户注册

| 项目 | 值 |
|---|---|
| 方法 | `POST` |
| URL | `/api/v1/auth/register` |
| 鉴权 | 不需要 |
| 请求头 | `Content-Type: application/json` |

请求体：

| 字段 | 类型 | 必填 | 约束 |
|---|---|---|---|
| username | string | 是 | 3-20 位，仅字母/数字/下划线 |
| password | string | 是 | **后端强制校验**：8-20 位、同时含字母和数字、不允许空格 |
| nickname | string | 否 | ≤ 50 字 |
| email | string | 否 | 邮箱格式，≤ 100 字，不可与其他账号重复 |

> 请求体不接受额外字段，传了未定义字段（如 `is_admin`）直接 422。

请求示例：

```json
{ "username": "zhangsan", "password": "Abcd1234", "nickname": "张三" }
```

成功响应 `201`：

```json
{
  "code": 201,
  "message": "注册成功",
  "data": {
    "id": 3,
    "username": "zhangsan",
    "nickname": "张三",
    "email": null,
    "created_at": "2026-10-14T20:55:43"
  }
}
```

错误码：

| 状态码 | 场景 | 响应 message |
|---|---|---|
| 400 | 密码长度不在 8-20 位 | `密码长度必须为 8-20 位` |
| 400 | 密码纯数字或纯字母 | `密码必须同时包含字母和数字` |
| 400 | 密码含空格 | `密码不能包含空格` |
| 400 | 密码为空字符串 | `密码不能为空` |
| 409 | 用户名已存在 | `用户名已存在，请更换后重试` |
| 409 | 邮箱已被注册 | `邮箱已被注册，请更换后重试` |
| 422 | 用户名格式非法（如 `ab`） | `请求参数校验失败`，`errors[0].field = body.username` |
| 422 | 密码类型错误（如传数字 `12345678`） | `errors[0].field = body.password` |
| 422 | 缺少必填字段 | `errors[0].field = body.password`，`type = missing` |

### 2.2 用户登录

| 项目 | 值 |
|---|---|
| 方法 | `POST` |
| URL | `/api/v1/auth/login` |
| 鉴权 | 不需要 |

请求体：

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| username | string | 是 | 登录名 |
| password | string | 是 | 明文密码（HTTPS 传输，服务端 bcrypt 比对） |

请求示例：

```json
{ "username": "demo", "password": "Demo1234" }
```

成功响应 `200`：

```json
{
  "code": 200,
  "message": "登录成功",
  "data": {
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "token_type": "bearer",
    "expires_in": 7200,
    "user": { "id": 1, "username": "demo", "nickname": "演示账号", "email": "demo@example.com", "created_at": "2026-10-14T20:51:03" }
  }
}
```

错误码：

| 状态码 | 场景 | message |
|---|---|---|
| 401 | 用户名不存在 **或** 密码错误（提示语完全一致，防止账号枚举） | `用户名或密码错误` |
| 403 | 账号被停用（`is_active = 0`） | `账号已被停用，请联系管理员` |
| 422 | 缺少 username / password | `请求参数校验失败` |

### 2.3 获取当前登录用户

| 项目 | 值 |
|---|---|
| 方法 | `GET` |
| URL | `/api/v1/auth/me` |
| 鉴权 | 需要 |

成功响应 `200`：`data` 为当前用户对象（结构同注册响应）。

错误码：

| 状态码 | 场景 | message |
|---|---|---|
| 401 | 未带 Authorization 头 | `缺少访问令牌，请先登录` |
| 401 | Token 非法 | `无效的访问令牌` |
| 401 | Token 过期 | `登录状态已过期，请重新登录` |

---

## 三、分类

### 3.1 分类列表

| 项目 | 值 |
|---|---|
| 方法 | `GET` |
| URL | `/api/v1/categories` |
| 鉴权 | 需要 |

Query 参数：

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| type | string | 否 | `income` / `expense`，不传返回全部 |

成功响应 `200`：

```json
{
  "code": 200,
  "message": "success",
  "data": [
    { "id": 1, "name": "餐饮", "type": "expense", "icon": "🍜", "sort_order": 10, "is_system": true, "created_at": "2026-10-14T20:51:03" },
    { "id": 16, "name": "宠物", "type": "expense", "icon": "🐱", "sort_order": 0, "is_system": false, "created_at": "2026-10-14T20:55:43" }
  ]
}
```

> `is_system = true` 表示系统预置分类，所有用户可见且不可修改、删除。

错误码：`401`（未认证）、`422`（`type` 传了非枚举值）。

### 3.2 新建自定义分类

| 项目 | 值 |
|---|---|
| 方法 | `POST` |
| URL | `/api/v1/categories` |
| 鉴权 | 需要 |

请求体：

| 字段 | 类型 | 必填 | 约束 |
|---|---|---|---|
| name | string | 是 | 1-30 字（前后空格自动去除） |
| type | string | 是 | `income` / `expense` |
| icon | string | 否 | ≤ 50 字，建议 emoji |
| sort_order | number | 否 | 0-9999，默认 0，越小越靠前 |

请求示例：

```json
{ "name": "宠物", "type": "expense", "icon": "🐱", "sort_order": 100 }
```

成功响应 `201`：`data` 为新建的分类对象。

错误码：

| 状态码 | 场景 | message |
|---|---|---|
| 409 | 同类型下已有同名自定义分类 | `分类名称已存在` |
| 409 | 与系统预置分类重名 | `分类名称与系统预置分类重复，请换一个名称` |
| 422 | `type` 传 `transfer` 等非法枚举 | `请求参数校验失败` |
| 422 | `name` 为空 | `请求参数校验失败` |

### 3.3 修改自定义分类

| 项目 | 值 |
|---|---|
| 方法 | `PUT` |
| URL | `/api/v1/categories/{category_id}` |
| 鉴权 | 需要 |

请求体（只需传要改的字段，`type` 不支持修改，传了会 422）：

```json
{ "name": "宠物用品", "icon": "🐶", "sort_order": 5 }
```

成功响应 `200`：`data` 为更新后的分类对象。

错误码：

| 状态码 | 场景 | message |
|---|---|---|
| 400 | 请求体里没有任何可更新字段（`{}`） | `没有需要更新的字段` |
| 403 | 目标是系统预置分类 | `系统预置分类不允许修改` |
| 404 | 分类不存在或属于其他用户 | `分类不存在` |
| 409 | 改名后与已有分类重名 | `分类名称已存在` |

### 3.4 删除自定义分类

| 项目 | 值 |
|---|---|
| 方法 | `DELETE` |
| URL | `/api/v1/categories/{category_id}` |
| 鉴权 | 需要 |

成功响应 `204`：**无响应体**。

错误码：

| 状态码 | 场景 | message |
|---|---|---|
| 400 | 该分类下还有未删除的记账记录 | `该分类下还有 3 条记账记录，请先删除或调整这些记录` |
| 403 | 系统预置分类 | `系统预置分类不允许删除` |
| 404 | 分类不存在 / 已删除 / 属于他人 | `分类不存在` |

---

## 四、收支明细

### 4.1 新增收支记录

| 项目 | 值 |
|---|---|
| 方法 | `POST` |
| URL | `/api/v1/transactions` |
| 鉴权 | 需要 |

请求体：

| 字段 | 类型 | 必填 | 约束 |
|---|---|---|---|
| type | string | 是 | `income` / `expense` |
| amount | number \| string | 是 | **必须 > 0**，最多两位小数，最大 `9999999999.99` |
| category_id | number | 是 | 必须存在，且 `category.type` 与 `type` 一致 |
| occurred_at | string | 是 | 记账日期 `YYYY-MM-DD` |
| remark | string | 否 | ≤ 255 字 |

请求示例：

```json
{
  "type": "expense",
  "amount": "25.80",
  "category_id": 1,
  "occurred_at": "2026-10-14",
  "remark": "和同事午餐"
}
```

成功响应 `201`：

```json
{
  "code": 201,
  "message": "创建成功",
  "data": {
    "id": 3,
    "type": "expense",
    "amount": "25.80",
    "category_id": 1,
    "category_name": "餐饮",
    "category_icon": "🍜",
    "remark": "和同事午餐",
    "occurred_at": "2026-10-14",
    "created_at": "2026-10-14T20:55:43",
    "updated_at": "2026-10-14T20:55:43"
  }
}
```

错误码：

| 状态码 | 场景 | message |
|---|---|---|
| 400 | `amount` = 0 | `金额必须大于 0` |
| 400 | `amount` = -100 | `金额必须大于 0` |
| 400 | `amount` = 10.999 | `金额最多保留两位小数` |
| 400 | `category_id` 不存在 / 属于其他用户 | `分类不存在或不属于当前用户` |
| 400 | 分类类型与 `type` 不一致 | `分类「餐饮」的收支类型与本次提交的 type 不一致` |
| 401 | 未认证 | `缺少访问令牌，请先登录` |
| 422 | `amount` = `"abc"` | `请求参数校验失败` + `errors[0] = {field: "body.amount", type: "decimal_parsing"}` |
| 422 | `amount` 超出字段精度（如 `1234567890123`） | `请求参数校验失败`，`type = decimal_max_digits` |
| 422 | `type` = `"transfer"` | `请求参数校验失败`，`type = enum` |
| 422 | `occurred_at` = `"2026-13-45"` | `请求参数校验失败`，`type = date_from_datetime_parsing` |
| 422 | `remark` 超过 255 字 | `请求参数校验失败`，`type = string_too_long` |

### 4.2 收支明细列表

| 项目 | 值 |
|---|---|
| 方法 | `GET` |
| URL | `/api/v1/transactions` |
| 鉴权 | 需要 |

Query 参数：

| 参数 | 类型 | 默认 | 说明 |
|---|---|---|---|
| page | number | 1 | ≥ 1 |
| page_size | number | 20 | 1-100 |
| type | string | — | `income` / `expense` |
| category_id | number | — | 按分类筛选 |
| start_date | string | — | 记账日期 ≥ 该日期 |
| end_date | string | — | 记账日期 ≤ 该日期 |
| keyword | string | — | 备注模糊匹配，≤ 50 字 |
| sort_by | string | `occurred_at` | `occurred_at` / `amount` / `created_at` |
| order | string | `desc` | `asc` / `desc` |

请求示例：`GET /api/v1/transactions?page=1&page_size=2&type=income`

成功响应 `200`：

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "items": [
      {
        "id": 4, "type": "income", "amount": "1000.00",
        "category_id": 10, "category_name": "工资", "category_icon": "💰",
        "remark": "10 月工资", "occurred_at": "2026-10-14",
        "created_at": "2026-10-14T20:55:43", "updated_at": "2026-10-14T20:55:43"
      }
    ],
    "total": 2, "page": 1, "page_size": 2, "pages": 1
  }
}
```

错误码：

| 状态码 | 场景 | message |
|---|---|---|
| 400 | `start_date` 晚于 `end_date` | `开始日期不能晚于结束日期` |
| 401 | 未认证 | `缺少访问令牌，请先登录` |
| 422 | `page=abc` | `errors[0].field = query.page` |
| 422 | `page_size=500` | `errors[0].field = query.page_size` |
| 422 | `sort_by=xx` / `order=up` | `errors[0].field = query.sort_by` |

> 页码超出范围不报错，返回 `items: []`，`total` 仍为真实总数。

### 4.3 收支明细详情

| 项目 | 值 |
|---|---|
| 方法 | `GET` |
| URL | `/api/v1/transactions/{transaction_id}` |
| 鉴权 | 需要 |

成功响应 `200`：`data` 为单条记录（结构同 4.1 响应）。

错误码：

| 状态码 | 场景 | message |
|---|---|---|
| 404 | 记录不存在 / 已软删除 / 属于其他用户 | `记录不存在或已被删除` |
| 422 | `transaction_id` 不是数字（如 `abc`） | `请求参数校验失败` |

### 4.4 修改收支记录

| 项目 | 值 |
|---|---|
| 方法 | `PUT` |
| URL | `/api/v1/transactions/{transaction_id}` |
| 鉴权 | 需要 |

请求体（**部分更新**，只传要改的字段）：

| 字段 | 类型 | 说明 |
|---|---|---|
| type | string | `income` / `expense` |
| amount | number \| string | 必须 > 0，最多两位小数 |
| category_id | number | 与最终 type 必须匹配 |
| occurred_at | string | `YYYY-MM-DD` |
| remark | string \| null | 传 `null` 表示清空备注 |

请求示例：

```json
{ "amount": "30.00", "remark": "改过了" }
```

成功响应 `200`：`data` 为更新后的记录。

错误码：

| 状态码 | 场景 | message |
|---|---|---|
| 400 | 请求体为空 `{}` | `没有需要更新的字段` |
| 400 | `amount` = 0 或 -1 | `金额必须大于 0` |
| 400 | `amount` = `null`（显式传空） | `金额不能为空` |
| 400 | 只改 `type` 未改 `category_id`，导致类型不匹配 | `分类「餐饮」的收支类型与本次提交的 type 不一致` |
| 404 | 记录不存在 / 已删除 / 属于他人 | `记录不存在或已被删除` |

### 4.5 删除收支记录

| 项目 | 值 |
|---|---|
| 方法 | `DELETE` |
| URL | `/api/v1/transactions/{transaction_id}` |
| 鉴权 | 需要 |

成功响应 `204`：**无响应体**。

> 采用**软删除**：库中 `is_deleted` 置 1，记录不再出现在任何查询里，重复删除返回 404，数据仍可在库中追溯。

错误码：`404`（不存在、已删除、属于他人）。

### 4.6 收支汇总

| 项目 | 值 |
|---|---|
| 方法 | `GET` |
| URL | `/api/v1/transactions/summary` |
| 鉴权 | 需要 |

Query 参数：`type`、`category_id`、`start_date`、`end_date`（与列表接口一致的筛选口径，不含分页）。

成功响应 `200`：

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "total_income": "1000.00",
    "total_expense": "25.80",
    "balance": "974.20",
    "income_count": 1,
    "expense_count": 1,
    "start_date": null,
    "end_date": null
  }
}
```

错误码：`400`（日期区间非法）、`401`、`422`（`type`/日期格式非法）。

---

## 五、健康检查

| 项目 | 值 |
|---|---|
| 方法 | `GET` |
| URL | `/api/v1/health` |
| 鉴权 | 不需要 |

> 注意：该接口不返回统一响应体（便于对接探活工具）。

成功响应 `200`：

```json
{
  "status": "ok",
  "app": "个人记账本",
  "version": "1.0.0",
  "database": "ok",
  "server_time": "2026-10-14T20:55:43.587024"
}
```

数据库不可用时：HTTP 仍为 `200`，但 `status = "degraded"`、`database = "error"`。

---

## 六、Apifox / Postman 使用提示

1. **导入接口**：Apifox → 项目设置 → 导入数据 → 选择 OpenAPI/Swagger → 填 `http://localhost:8000/openapi.json`。
2. **设置公共变量**：`baseUrl = http://localhost:8000`、`token = <登录返回的 access_token>`。
3. **公共请求头**：`Authorization: Bearer {{token}}`。
4. **建议的联调顺序**：注册 → 登录（存 token）→ 分类列表（拿 `category_id`）→ 新增记录 → 列表 → 汇总 → 修改 → 删除。
5. 需要额外造数据时，可直接执行 `backend/sql/02_seed.sql` 里的预置分类，或调用 `POST /categories` 自建。
