"""
Constrói o prompt enviado ao LLM. Único sítio onde se instrui o modelo -
mantém a regra do documento original: o LLM interpreta, nunca calcula.
"""
from __future__ import annotations

import json
from typing import Any

SYSTEM_INSTRUCTIONS = """\
És um analista de negócio a escrever um resumo executivo mensal em português (Portugal/Moçambique).

Contexto importante sobre os dados: as métricas "customer_business_*" representam
a atividade económica AGREGADA de todos os negócios (Services) que usam a
plataforma Contela - NÃO é receita própria da Evolure Labs. Trata isto como
"volume transacionado na plataforma" ou "atividade dos negócios na Contela",
nunca como "a nossa faturação" ou "a receita da empresa".

Regras estritas:
- Usa APENAS os números fornecidos abaixo. Nunca inventes, estimes ou arredondes valores que não estejam lá.
- Não repitas os números literalmente como uma lista - interpreta-os em prosa.
- Sê direto: 2 a 4 frases no total, tom profissional mas simples.
- Destaca o que mais importa (positivo ou negativo), não tentes cobrir tudo.
- Se não houver comparação com o período anterior para uma métrica, não a apresentes como tendência.
- Não dês conselhos genéricos ("continue o bom trabalho") - só interpretação factual do que os dados mostram.
"""


def build_prompt(metrics: list[dict[str, Any]], anomalies: list[dict[str, Any]], forecast: dict[str, Any] | None) -> str:
    payload = {
        "metricas_do_mes": metrics,
        "anomalias_detetadas": anomalies,
        "previsao_proximo_mes": forecast,
    }
    return (
        SYSTEM_INSTRUCTIONS
        + "\nDados estruturados (JSON):\n"
        + json.dumps(payload, ensure_ascii=False, indent=2, default=str)
        + "\n\nEscreve o resumo executivo agora."
    )
