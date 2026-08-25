"""
Utilitários partilhados por qualquer Analyzer que compare métricas por
período ("YYYY-MM") com o período anterior. Extraído do SalesAnalyzer para
não repetir a mesma lógica de datas em cada Analyzer novo.
"""
from __future__ import annotations

from datetime import date


def period_bounds(period: str) -> tuple[date, date]:
    """'YYYY-MM' -> (primeiro dia do mês, primeiro dia do mês seguinte)."""
    year, month = map(int, period.split("-"))
    start = date(year, month, 1)
    end = date(year + 1, 1, 1) if month == 12 else date(year, month + 1, 1)
    return start, end


def previous_period(period: str) -> str:
    year, month = map(int, period.split("-"))
    if month == 1:
        return f"{year - 1}-12"
    return f"{year}-{month - 1:02d}"


def next_period(period: str) -> str:
    year, month = map(int, period.split("-"))
    if month == 12:
        return f"{year + 1}-01"
    return f"{year}-{month + 1:02d}"


def status_for_change(change: float | None) -> str:
    if change is None:
        return "neutral"  # sem período anterior para comparar
    if change > 0:
        return "positive"
    if change < 0:
        return "negative"
    return "neutral"
