"""FR-503 交付物管理核心工具函数——严格对齐 prd1_5.md 簇 D"""
from app.core.constants import FORBIDDEN_FIELD_PATTERNS


def contains_password_field(handover_item: dict) -> bool:
    """
    检测账号交接条目的 JSON 字段名（不是字段值）是否含有禁止字符串。
    检测方式：将字段名转为小写，判断是否包含 FORBIDDEN_FIELD_PATTERNS 中任意子串。
    不得扫描字段值内容。
    """
    for field_name in handover_item.keys():
        lower_name = field_name.lower()
        for pattern in FORBIDDEN_FIELD_PATTERNS:
            if pattern in lower_name:
                return True
    return False
