# 校验责任矩阵（前端 vs 后端）

> 这份文档回答一个问题：**每个校验点到底该测前端弹窗，还是该绕过前端、用 Postman 直接打接口测后端防御？**
>
> 结论先给：**所有安全与业务规则后端都独立校验了一遍**，前端校验只是为了体验，不承担安全责任。

## 一、四层校验模型

| 层级 | 位置 | 职责 | 失败时的表现 |
|---|---|---|---|
| **L1 前端（体验层）** | `frontend/static/js/validate.js` + `login.js` / `app.js` | 提前拦截，减少无意义请求 | `window.alert(...)` 弹窗，**不发请求** |
| **L2 后端结构层** | `backend/app/schemas/*.py`（Pydantic v2） | 类型、必填、格式、枚举、长度上限、精度上限、未知字段 | **422** + `errors[]` 字段级明细 |
| **L3 后端业务层** | `backend/app/core/validators.py` + `backend/app/api/v1/*.py` | 密码策略、金额业务规则、归属与越权、分类一致性、唯一性 | **400 / 401 / 403 / 404 / 409** |
| **L4 数据库层** | `backend/sql/01_schema.sql` | 唯一索引、外键、`CHECK (amount > 0)`、`NOT NULL` | 最后兜底；注册并发冲突会被转成 409 |

**一句话记忆规则**：`422 = Pydantic 拦下来的（结构问题）`，`400 = 业务代码拦下来的（业务问题）`。

## 二、逐项对照表

图例：✅ = 该层有校验；— = 该层不涉及。

| # | 校验点 | L1 前端 | L2 Pydantic | L3 业务层 | 绕过前端时后端返回 |
|---|---|---|---|---|---|
| 1 | 用户名必填 | ✅ | ✅ `required` | — | 422，`field=body.username` |
| 2 | 用户名 3-20 位、仅字母数字下划线 | ✅ 正则 | ✅ `pattern` | ✅ 兜底 `validate_username` | 422，`field=body.username` |
| 3 | 用户名不可重复 | — | — | ✅ 查库 | 409 `用户名已存在，请更换后重试` |
| 4 | 邮箱格式 | ✅ 正则 | ✅ `pattern` | — | 422，`field=body.email` |
| 5 | 邮箱不可重复 | — | — | ✅ 查库 | 409 `邮箱已被注册，请更换后重试` |
| 6 | **密码长度 8-20 位** | ✅ | 刻意不加约束 | ✅ `validate_password_strength` | **400** `密码长度必须为 8-20 位` |
| 7 | **密码必须同时含字母和数字** | ✅ | 刻意不加约束 | ✅ | **400** `密码必须同时包含字母和数字` |
| 8 | **密码不能含空格** | ✅ | 刻意不加约束 | ✅ | **400** `密码不能包含空格` |
| 9 | **密码不能为空** | ✅ | 刻意不加约束 | ✅ | **400** `密码不能为空` |
| 10 | 密码必须是字符串类型 | ✅（输入框） | ✅ `str` | — | 422，`type=string_type` |
| 11 | 两次密码一致 | ✅ | — | —（接口无此字段） | 多传 `confirm_password` → 422 `extra_forbidden` |
| 12 | 密码加密存储（bcrypt 加盐） | — | — | ✅ `hash_password`（cost=12） | 查库确认 `$2b$12$...`，明文绝不落库 |
| 13 | 请求体禁止多余字段 | — | ✅ `extra="forbid"` | — | 422 `extra_forbidden` |
| 14 | **金额必须 > 0** | ✅ | 刻意不加约束 | ✅ `validate_amount` | **400** `金额必须大于 0` |
| 15 | **金额最多两位小数** | ✅ 输入过滤 + 提交前校验 | 刻意不加约束 | ✅ | **400** `金额最多保留两位小数` |
| 16 | 金额必须是数字（如 `"abc"`） | ✅ 输入框过滤非数字 | ✅ `Decimal` | — | 422，`field=body.amount`、`type=decimal_parsing` |
| 17 | 金额 ≤ `9999999999.99`（`DECIMAL(12,2)`） | ✅ | ✅ `max_digits=12` | ✅ 业务上限兜底 | 422，`type=decimal_max_digits` / `decimal_places` |
| 18 | 金额不能缺省 | ✅ | ✅ `required` | — | 422，`type=missing` |
| 19 | 收支类型只能是 income/expense | ✅ 下拉框 | ✅ 枚举 | — | 422，`type=enum` |
| 20 | 记账日期格式 `YYYY-MM-DD` | ✅ 日期控件 | ✅ `date` | — | 422，`type=date_from_datetime_parsing` |
| 21 | 备注 ≤ 255 字 | ✅ `maxlength` | ✅ `max_length` | — | 422，`type=string_too_long` |
| 22 | 备注自动去首尾空格 | ✅ | ✅ `strip_whitespace` | — | 自动处理（不算错误） |
| 23 | 分类必须存在 | ✅ 只能选已有分类 | — | ✅ 查库 | 400 `分类不存在或不属于当前用户` |
| 24 | 分类归属当前用户 | — | — | ✅ 查询带 `user_id` | 400 同上 |
| 25 | 分类的收支类型必须与 type 一致 | ✅ 下拉联动 | — | ✅ `_resolve_category` | 400 `分类「餐饮」的收支类型与本次提交的 type 不一致` |
| 26 | 分类名称不重复（同类型） | ✅ 提示 | — | ✅ 查库 | 409 `分类名称已存在` |
| 27 | 分类名不可与系统预置重复 | — | — | ✅ 查库 | 409 `分类名称与系统预置分类重复，请换一个名称` |
| 28 | 不能修改/删除系统预置分类 | —（界面不给入口） | — | ✅ 校验 `user_id is None` | 403 `系统预置分类不允许修改/删除` |
| 29 | 分类下仍有记录时不能删除 | — | — | ✅ 统计条数 | 400 `该分类下还有 N 条记账记录…` |
| 30 | 分类不能改类型 | — | ✅ 无该字段 | — | 422 `extra_forbidden` |
| 31 | 已删除记录不可再查/改/删 | ✅ 列表不展示 | — | ✅ 软删除 + 查询过滤 | 404 `记录不存在或已被删除` |
| 32 | 不能访问/修改他人数据 | — | — | ✅ 所有查询带 `user_id` | 404 |
| 33 | 未登录 / Token 非法 / 过期 | ✅ 跳转登录页 | — | ✅ `get_current_user` | 401 |
| 34 | 页码 ≥ 1、每页 1-100 | ✅ 前端固定 | ✅ `ge/le` | — | 422，`field=query.page_size` |
| 35 | 排序字段与方向只能取白名单值 | ✅ 前端固定 | ✅ `Literal`（SQL 注入防护） | — | 422，`field=query.sort_by` |
| 36 | 关键字 ≤ 50 字 | — | ✅ `max_length` | — | 422，`field=query.keyword` |
| 37 | 开始日期不得晚于结束日期 | — | — | ✅ 路由校验 | 400 `开始日期不能晚于结束日期` |
| 38 | 请求体必须是合法 JSON | — | ✅ | — | 422，`type=json_invalid` |

> 序号 6-9、14-15 就是本次特别强调的部分：**前端做了，后端也做了一遍**，Postman 直接打接口一样会被拦。

## 三、QA 分工建议

### 3.1 测「前端体验层」（L1）

在浏览器里操作即可，关注点是**弹窗文案 + 是否真的没发请求**：

1. 打开 `http://localhost:8000/login`，注册 Tab。
2. 密码填 `123456` → 应弹窗「密码长度必须为 8-20 位」，且 **Network 面板里没有任何 `/auth/register` 请求**。
3. 两次密码不一致 → 弹窗「两次输入的密码不一致」，同样不发请求。
4. 主页面点「＋ 记一笔」，金额框尝试输入 `-5`、`1.234` → 输入框会被实时过滤，无法输入非法字符；提交前仍会被 `checkAmount` 拦下。

### 3.2 测「后端防御层」（L2 / L3）——**用 Postman/Apifox 直接打接口，不要经过页面**

| 用例 | 方法与 URL | 请求体 | 期望 |
|---|---|---|---|
| 弱密码：太短 | `POST /api/v1/auth/register` | `{"username":"qa01","password":"123456"}` | **400** `密码长度必须为 8-20 位` |
| 弱密码：纯数字 | 同上 | `{"username":"qa01","password":"12345678"}` | **400** `密码必须同时包含字母和数字` |
| 弱密码：纯字母 | 同上 | `{"username":"qa01","password":"abcdefgh"}` | **400** `密码必须同时包含字母和数字` |
| 弱密码：含空格 | 同上 | `{"username":"qa01","password":"Abcd 1234"}` | **400** `密码不能包含空格` |
| 正常注册 | 同上 | `{"username":"qa01","password":"Abcd1234"}` | **201** |
| 用户名重复 | 同上 | 再发一次同样的请求 | **409** `用户名已存在，请更换后重试` |
| 用户名非法字符 | 同上 | `{"username":"qa@01","password":"Abcd1234"}` | **422** `field=body.username` |
| 用户名过短 | 同上 | `{"username":"ab","password":"Abcd1234"}` | **422** `field=body.username` |
| 密码类型错误 | 同上 | `{"username":"qa01","password":12345678}` | **422** `field=body.password` |
| 多余字段 | 同上 | `{"username":"qa01","password":"Abcd1234","is_admin":true}` | **422** `extra_forbidden` |
| 非 JSON 请求体 | 同上 | Body 选 raw/Text 填 `abc` | **422** `type=json_invalid` |
| 金额为 0 | `POST /api/v1/transactions` | `{"type":"expense","amount":"0","category_id":1,"occurred_at":"2026-10-14"}` | **400** `金额必须大于 0` |
| 金额为负 | 同上 | `amount: "-100"` | **400** `金额必须大于 0` |
| 金额三位小数 | 同上 | `amount: "10.999"` | **400** `金额最多保留两位小数` |
| 金额传 abc | 同上 | `amount: "abc"` | **422** + `errors[0]={field:"body.amount",type:"decimal_parsing"}` |
| 金额超字段上限 | 同上 | `amount: "1234567890123"` | **422** |
| 金额缺省 | 同上 | 请求体不含 amount | **422** `type=missing` |
| 类型非法 | 同上 | `type: "transfer"` | **422** `type=enum` |
| 日期非法 | 同上 | `occurred_at: "2026-13-45"` | **422** |
| 分类不存在 | 同上 | `category_id: 999999` | **400** `分类不存在或不属于当前用户` |
| 分类与类型不符 | 同上 | `type: "income"` + 支出分类 id | **400** `分类「餐饮」的收支类型与本次提交的 type 不一致` |
| 分页参数非法 | `GET /api/v1/transactions?page=abc` | — | **422** `field=query.page` |
| 每页超限 | `GET /api/v1/transactions?page_size=500` | — | **422** `field=query.page_size` |
| 排序字段注入 | `GET /api/v1/transactions?sort_by=remark` | — | **422** `field=query.sort_by` |
| 日期区间倒挂 | `GET /api/v1/transactions?start_date=2026-10-20&end_date=2026-10-01` | — | **400** `开始日期不能晚于结束日期` |
| 未带 Token | `GET /api/v1/transactions` | — | **401** `缺少访问令牌，请先登录` |
| Token 篡改 | 同上，`Authorization: Bearer abc.def.ghi` | — | **401** `无效的访问令牌` |
| 越权访问 | 用 A 的 Token 请求 B 的记录 id | — | **404** `记录不存在或已被删除` |
| 改系统预置分类 | `PUT /api/v1/categories/1` | `{"name":"改名"}` | **403** `系统预置分类不允许修改` |
| 删系统预置分类 | `DELETE /api/v1/categories/1` | — | **403** `系统预置分类不允许删除` |
| 删占用中的分类 | `DELETE /api/v1/categories/{自建分类id}` | 该分类下已有记录 | **400** `该分类下还有 N 条记账记录…` |

### 3.3 一遍跑完所有用例

不用手工点，直接跑脚本（会真实发 HTTP 请求）：

```bash
cd backend
python scripts/smoke_test.py --base-url http://localhost:8000
```

自动化回归（包含上表全部用例，共 86 条，无需 MySQL）：

```bash
cd backend
pytest -q
```

## 四、已知的可接受行为

1. **金额支持科学计数法写法**：`"1e3"` 会被解析为 `1000.00`（Pydantic `Decimal` 的原生行为）。如果 QA 认为必须禁止，请提 Bug，我在业务层加一条正则拦截。
2. **`DECIMAL(12,2)` 上限**在两处生效：Pydantic 的 `max_digits=12` 先返回 422，业务层的 `MAX_AMOUNT` 作为兜底，因此上限场景统一表现为 422。
3. **时间字段没有时区后缀**：库中存 MySQL `DATETIME`，接口原样返回服务器本地时间（例如 `2026-10-14T20:55:43`）。这是刻意选择，避免"接口显示 UTC、库里是本地时间"的不一致。
4. **软删除**：`DELETE` 后数据仍在表中（`is_deleted=1`），需要物理删除请单独提需求。
5. **未登录时的优先级**：鉴权在业务校验之前，所以未带 Token 时即使是非法请求体也返回 401 而不是 422。
