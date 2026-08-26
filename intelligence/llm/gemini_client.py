"""
Cliente fino para o Gemini (Google). Isolado propositadamente - se um dia
quiseres trocar de fornecedor de LLM (Anthropic, Groq, etc), este é o
único ficheiro que precisa de mudar; o resto da Intelligence Engine só
conhece generate_text(prompt) -> str.

Requer GEMINI_API_KEY no ambiente. Conta gratuita em https://aistudio.google.com
"""
from __future__ import annotations

import os

from google import genai
from google.genai import types

DEFAULT_MODEL = "gemini-3.6-flash"


def generate_text(prompt: str, model: str = DEFAULT_MODEL) -> str:
    api_key = os.environ.get("GEMINI_API_KEY", "")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY não está definido")

    client = genai.Client(api_key=api_key)
    try:
        thinking_config = types.ThinkingConfig(thinking_level="low")
    except Exception:
        # SDK antigo sem suporte a thinking_level - usa thinking_budget (universal)
        thinking_config = types.ThinkingConfig(thinking_budget=256)

    response = client.models.generate_content(
        model=model,
        contents=prompt,
        config=types.GenerateContentConfig(
            temperature=0.4,  # baixa - queremos interpretação sóbria, não criatividade
            max_output_tokens=1024,  # margem generosa: tokens de "thinking" contam para este limite
            thinking_config=thinking_config,
        ),
    )
    return (response.text or "").strip()
