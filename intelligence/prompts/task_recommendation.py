"""
Constrói o prompt que pede ao LLM uma recomendação estruturada (JSON), a
partir do insight já gerado (Fase 5). É a ponte entre "Business Insight"
e "Task" do diagrama original: Insight -> Recommendation -> Task.
"""
from __future__ import annotations

SYSTEM_INSTRUCTIONS = """\
És um consultor de operações a converter um insight de negócio numa única
tarefa acionável e concreta, em português (Portugal/Moçambique).

Regras estritas:
- Baseia a tarefa apenas no insight fornecido - não inventes problemas que ele não menciona.
- A tarefa tem de ser específica e executável por uma pessoa, não um conselho vago.
- Responde APENAS com um objeto JSON válido, sem texto antes ou depois, com exatamente estes campos:
  {
    "title": "título curto da tarefa, máx. 10 palavras",
    "description": "1-2 frases explicando o que fazer e porquê",
    "priority": "low" | "medium" | "high",
    "category": "uma palavra ou duas, ex: vendas, stock, clientes, financeiro",
    "expected_impact": "low" | "medium" | "high"
  }
"""


def build_task_prompt(insight_text: str) -> str:
    return f"{SYSTEM_INSTRUCTIONS}\nInsight do mês:\n{insight_text}\n\nDevolve o JSON agora."
