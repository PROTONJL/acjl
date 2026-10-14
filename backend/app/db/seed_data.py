"""初始数据定义（系统预置分类）。"""

from __future__ import annotations

from typing import Dict, List

from app.models.enums import TransactionType


def _category(name: str, icon: str, sort_order: int, tx_type: TransactionType) -> Dict:
    return {
        "name": name,
        "icon": icon,
        "sort_order": sort_order,
        "type": tx_type,
    }


# user_id 为 None 表示系统预置分类，所有用户可见且不可删改
PRESET_CATEGORIES: List[Dict] = [
    _category("餐饮", "🍜", 10, TransactionType.EXPENSE),
    _category("交通", "🚌", 20, TransactionType.EXPENSE),
    _category("购物", "🛍️", 30, TransactionType.EXPENSE),
    _category("居住", "🏠", 40, TransactionType.EXPENSE),
    _category("娱乐", "🎮", 50, TransactionType.EXPENSE),
    _category("医疗", "💊", 60, TransactionType.EXPENSE),
    _category("教育", "📚", 70, TransactionType.EXPENSE),
    _category("通讯", "📱", 80, TransactionType.EXPENSE),
    _category("其他支出", "📦", 90, TransactionType.EXPENSE),
    _category("工资", "💰", 10, TransactionType.INCOME),
    _category("奖金", "🏆", 20, TransactionType.INCOME),
    _category("兼职", "🧰", 30, TransactionType.INCOME),
    _category("投资收益", "📈", 40, TransactionType.INCOME),
    _category("红包", "🧧", 50, TransactionType.INCOME),
    _category("其他收入", "✨", 60, TransactionType.INCOME),
]

# 演示账号（仅在执行 init_db 且显式开启时创建）
DEMO_USERNAME = "demo"
DEMO_PASSWORD = "Demo1234"
DEMO_NICKNAME = "演示账号"
