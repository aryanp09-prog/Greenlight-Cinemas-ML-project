"""
Greenlight Cinema — core pure-Python logic, mirrored from the Colab notebook.

The live backend runs in Colab (Ollama + LangGraph + FastAPI), but the two
*deterministic* pieces — the Critic validator and the prompt parser's guardrails
— are pure functions with no GPU/LLM dependency. They are duplicated here so they
can be unit-tested on the laptop with `pytest`. Keep these in sync with the
notebook cells (validator = CELL "PHASE 8", parser = the "import json, re" cell).
"""
