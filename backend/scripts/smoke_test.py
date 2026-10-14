"""接口冒烟测试脚本（针对**真实运行中的服务**，包含真实 MySQL 链路）。

与 ``tests/`` 下的 pytest 用例不同，本脚本不做任何 mock，
直接对你启动的服务发真实 HTTP 请求，适合部署后或回归前快速体检。

用法::

    python scripts/smoke_test.py                         # 默认 http://127.0.0.1:8000
    python scripts/smoke_test.py --base-url http://192.168.1.10:8000

退出码：0 = 全部通过；1 = 存在失败项。
"""

from __future__ import annotations

import argparse
import json
import random
import string
import sys
import urllib.error
import urllib.request
from datetime import date
from typing import Any, Optional, Tuple

PASSWORD = "Abcd1234"


def call(
    base_url: str,
    method: str,
    path: str,
    body: Optional[dict] = None,
    token: Optional[str] = None,
    params: Optional[dict] = None,
) -> Tuple[int, Any]:
    """发一个请求，返回 (HTTP 状态码, 响应体)。"""
    url = base_url.rstrip("/") + path
    if params:
        query = "&".join(f"{k}={v}" for k, v in params.items() if v not in (None, ""))
        if query:
            url += "?" + query

    data = json.dumps(body).encode("utf-8") if body is not None else None
    request = urllib.request.Request(url, data=data, method=method)
    request.add_header("Accept", "application/json")
    if data is not None:
        request.add_header("Content-Type", "application/json")
    if token:
        request.add_header("Authorization", f"Bearer {token}")

    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            raw = response.read().decode("utf-8")
            return response.status, (json.loads(raw) if raw else None)
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8")
        try:
            return exc.code, json.loads(raw)
        except json.JSONDecodeError:
            return exc.code, {"raw": raw}


class Checker:
    def __init__(self) -> None:
        self.passed = 0
        self.failed: list[str] = []

    def check(self, name: str, actual: Any, expected: Any) -> None:
        ok = actual == expected
        if ok:
            self.passed += 1
            print(f"  [PASS] {name}")
        else:
            self.failed.append(f"{name} | 期望={expected!r} 实际={actual!r}")
            print(f"  [FAIL] {name} | 期望={expected!r} 实际={actual!r}")

    def truthy(self, name: str, value: Any) -> None:
        self.check(name, bool(value), True)


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="个人记账本接口冒烟测试")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000", help="服务地址")
    args = parser.parse_args(argv)
    base = args.base_url.rstrip("/")
    api = base + "/api/v1"
    checker = Checker()
    username = "smoke_" + "".join(random.choices(string.ascii_lowercase, k=6))
    today = date.today().isoformat()

    print(f"\n目标服务：{base}")

    print("\n[1] 健康检查")
    status, body = call(base, "GET", "/api/v1/health")
    checker.check("GET /health 状态码", status, 200)
    checker.check("数据库连通", (body or {}).get("database"), "ok")

    print("\n[2] 注册与登录")
    status, body = call(
        api,
        "POST",
        "/auth/register",
        {"username": username, "password": PASSWORD, "nickname": "冒烟测试"},
    )
    checker.check("注册成功", status, 201)
    status, body = call(api, "POST", "/auth/login", {"username": username, "password": PASSWORD})
    checker.check("登录成功", status, 200)
    token = (body or {}).get("data", {}).get("access_token")
    checker.truthy("拿到 access_token", token)
    if not token:
        print("\n登录失败，后续用例无法继续")
        return 1

    status, body = call(api, "GET", "/auth/me", token=token)
    checker.check("GET /auth/me", status, 200)
    checker.check("用户名一致", (body or {}).get("data", {}).get("username"), username)

    print("\n[3] 鉴权防御")
    status, _ = call(api, "GET", "/transactions")
    checker.check("无 Token 访问明细返回 401", status, 401)
    status, _ = call(api, "GET", "/transactions", token="invalid.token.value")
    checker.check("非法 Token 返回 401", status, 401)

    print("\n[4] 后端密码策略（绕过前端直接调接口）")
    for weak, reason in [
        ("123456", "长度不足"),
        ("abcdefgh", "缺少数字"),
        ("12345678", "缺少字母"),
        ("Abcd 1234", "包含空格"),
    ]:
        status, body = call(
            api,
            "POST",
            "/auth/register",
            {"username": "weak_" + "".join(random.choices(string.ascii_lowercase, k=5)), "password": weak},
        )
        checker.check(f"弱密码 {weak!r}（{reason}）返回 400", status, 400)

    print("\n[5] 参数校验（422 字段级明细）")
    status, body = call(api, "POST", "/auth/register", {"username": username, "password": 12345678})
    checker.check("密码类型错误返回 422", status, 422)
    checker.truthy("返回字段级 errors", (body or {}).get("errors"))

    print("\n[6] 分类列表")
    status, body = call(api, "GET", "/categories", token=token)
    checker.check("分类列表 200", status, 200)
    categories = (body or {}).get("data") or []
    checker.truthy("存在系统预置分类", categories and all(c["is_system"] for c in categories))
    expense_id = next((c["id"] for c in categories if c["type"] == "expense"), None)
    income_id = next((c["id"] for c in categories if c["type"] == "income"), None)

    print("\n[7] 记账：金额边界")
    status, _ = call(
        api,
        "POST",
        "/transactions",
        {"type": "expense", "amount": "0", "category_id": expense_id, "occurred_at": today},
        token=token,
    )
    checker.check("金额 0 返回 400", status, 400)
    status, _ = call(
        api,
        "POST",
        "/transactions",
        {"type": "expense", "amount": "-100", "category_id": expense_id, "occurred_at": today},
        token=token,
    )
    checker.check("金额 -100 返回 400", status, 400)
    status, _ = call(
        api,
        "POST",
        "/transactions",
        {"type": "expense", "amount": "10.999", "category_id": expense_id, "occurred_at": today},
        token=token,
    )
    checker.check("三位小数返回 400", status, 400)
    status, body = call(
        api,
        "POST",
        "/transactions",
        {"type": "expense", "amount": "abc", "category_id": expense_id, "occurred_at": today},
        token=token,
    )
    checker.check("金额传 abc 返回 422", status, 422)
    checker.check(
        "422 errors[0].field",
        ((body or {}).get("errors") or [{}])[0].get("field"),
        "body.amount",
    )

    print("\n[8] 记账：正常流程")
    status, body = call(
        api,
        "POST",
        "/transactions",
        {
            "type": "expense",
            "amount": "25.80",
            "category_id": expense_id,
            "occurred_at": today,
            "remark": "冒烟-午餐",
        },
        token=token,
    )
    checker.check("新增支出 201", status, 201)
    tx_id = (body or {}).get("data", {}).get("id")
    checker.check("金额格式为两位小数字符串", (body or {}).get("data", {}).get("amount"), "25.80")

    status, body = call(
        api,
        "POST",
        "/transactions",
        {
            "type": "income",
            "amount": "1000",
            "category_id": income_id,
            "occurred_at": today,
            "remark": "冒烟-工资",
        },
        token=token,
    )
    checker.check("新增收入 201", status, 201)

    status, _ = call(
        api,
        "POST",
        "/transactions",
        {"type": "income", "amount": "10", "category_id": expense_id, "occurred_at": today},
        token=token,
    )
    checker.check("分类与类型不匹配返回 400", status, 400)

    print("\n[9] 明细列表 / 汇总")
    status, body = call(api, "GET", "/transactions", token=token, params={"page": 1, "page_size": 10})
    checker.check("列表 200", status, 200)
    checker.check("总数", (body or {}).get("data", {}).get("total"), 2)
    status, body = call(
        api, "GET", "/transactions", token=token, params={"type": "income", "page_size": 10}
    )
    checker.check("按类型筛选", (body or {}).get("data", {}).get("total"), 1)
    status, body = call(api, "GET", "/transactions", token=token, params={"page": "abc"})
    checker.check("page=abc 返回 422", status, 422)

    status, body = call(api, "GET", "/transactions/summary", token=token)
    data = (body or {}).get("data", {})
    checker.check("总收入", data.get("total_income"), "1000.00")
    checker.check("总支出", data.get("total_expense"), "25.80")
    checker.check("结余", data.get("balance"), "974.20")

    print("\n[10] 修改 / 删除")
    status, body = call(
        api, "PUT", f"/transactions/{tx_id}", {"amount": "30.00", "remark": "冒烟-改"}, token=token
    )
    checker.check("修改成功", status, 200)
    checker.check("修改后金额", (body or {}).get("data", {}).get("amount"), "30.00")
    status, _ = call(api, "DELETE", f"/transactions/{tx_id}", token=token)
    checker.check("删除返回 204", status, 204)
    status, _ = call(api, "GET", f"/transactions/{tx_id}", token=token)
    checker.check("删除后查询返回 404", status, 404)

    print("\n" + "=" * 56)
    print(f"通过 {checker.passed} 项，失败 {len(checker.failed)} 项")
    for item in checker.failed:
        print("  - " + item)
    print("=" * 56 + "\n")
    return 1 if checker.failed else 0


if __name__ == "__main__":
    sys.exit(main())
