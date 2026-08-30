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


def validate_sale(record: dict[str, Any]) -> tuple[bool, str | None]:
    total = record.get("total_amount")
    if total is None:
        return False, "total_amount em falta"
    if total < 0:
        return False, "total_amount negativo"
    if not record.get("sale_date"):
        return False, "sale_date em falta"
    cogs = record.get("cogs")
    if cogs is not None and cogs < 0:
        return False, "cogs negativo"
    return True, None


def validate_organization(record: dict[str, Any]) -> tuple[bool, str | None]:
    if not record.get("name"):
        return False, "name em falta"
    if record.get("org_type") not in ("SERVICE", "SUPPLIER"):
        return False, "org_type inválido"
    return True, None


# --- Webstudio ---

def validate_client(record: dict[str, Any]) -> tuple[bool, str | None]:
    if not record.get("name"):
        return False, "name em falta"
    return True, None


def validate_lead(record: dict[str, Any]) -> tuple[bool, str | None]:
    if not record.get("name"):
        return False, "name em falta"
    if not record.get("status"):
        return False, "status em falta"
    return True, None


def validate_proposal(record: dict[str, Any]) -> tuple[bool, str | None]:
    total = record.get("total_amount")
    if total is None:
        return False, "total_amount em falta"
    if total < 0:
        return False, "total_amount negativo"
    if not record.get("status"):
        return False, "status em falta"
    return True, None


def validate_contract(record: dict[str, Any]) -> tuple[bool, str | None]:
    value = record.get("value")
    if value is None:
        return False, "value em falta"
    if value < 0:
        return False, "value negativo"
    return True, None


def validate_project(record: dict[str, Any]) -> tuple[bool, str | None]:
    if not record.get("name"):
        return False, "name em falta"
    if not record.get("status"):
        return False, "status em falta"
    return True, None


def validate_invoice(record: dict[str, Any]) -> tuple[bool, str | None]:
    total = record.get("total")
    if total is None:
        return False, "total em falta"
    if total < 0:
        return False, "total negativo"
    return True, None


def validate_payment(record: dict[str, Any]) -> tuple[bool, str | None]:
    amount = record.get("amount")
    if amount is None:
        return False, "amount em falta"
    if amount < 0:
        return False, "amount negativo"
    return True, None


def validate_expense(record: dict[str, Any]) -> tuple[bool, str | None]:
    amount = record.get("amount")
    if amount is None:
        return False, "amount em falta"
    if amount < 0:
        return False, "amount negativo"
    return True, None


def validate_campaign(record: dict[str, Any]) -> tuple[bool, str | None]:
    if not record.get("name"):
        return False, "name em falta"
    return True, None
