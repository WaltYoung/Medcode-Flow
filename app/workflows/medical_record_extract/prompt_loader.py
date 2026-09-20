from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from jinja2 import Environment, BaseLoader, StrictUndefined

PROMPTS_DIR = Path(__file__).resolve().parent / "prompts"

_env = Environment(
    loader=BaseLoader(),
    undefined=StrictUndefined,
    autoescape=False,
)


@lru_cache
def _read_prompt(name: str) -> str:
    path = PROMPTS_DIR / name
    if not path.exists():
        raise FileNotFoundError(f"Prompt not found: {path}")
    return path.read_text(encoding="utf-8")


def render_prompt(name: str, **variables: object) -> str:
    template = _env.from_string(_read_prompt(name))
    return template.render(**variables)
