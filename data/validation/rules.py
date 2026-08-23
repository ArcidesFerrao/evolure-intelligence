"""
Regras de validação para promover staging -> core.

Genéricas o suficiente para qualquer fonte (não são específicas do Contela) -
quando o Webstudio ou outro Lab começar a alimentar "orders", passa por
aqui também.
"""
from __future__ import annotations

from typing import Any


def validate_order(record: dict[str, Any]) -> tuple[bool, str | None]:
    if not record.get("customer_name"):
        return False, "customer_name em falta"
    total = record.get("total_amount")
    if total is None:
        return False, "total_amount em falta"
    if total < 0:
        return False, "total_amount negativo"
    if not record.get("order_date"):
        return False, "order_date em falta"
    if not record.get("status"):
        return False, "status em falta"
    return True, None


def validate_stock(record: dict[str, Any]) -> tuple[bool, str | None]:
    if not record.get("product_name"):
        return False, "product_name em falta"
    quantity = record.get("quantity")
    if quantity is None:
        return False, "quantity em falta"
    if quantity < 0:
        return False, "quantity negativa"
    return True, None
