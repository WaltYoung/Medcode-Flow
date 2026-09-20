from __future__ import annotations

from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from app.core.llm import get_llm_factory
from app.workflows.secondary_diagnosis.prompt_loader import render_prompt


def invoke_llm(
    *,
    system: str,
    user: str,
    mock_hint: str,
    mock_output: str,
) -> str:
    llm = get_llm_factory().get(
        mock_responses={mock_hint: mock_output},
    )
    response = llm.invoke(
        [SystemMessage(content=system), HumanMessage(content=user)]
    )
    content = response.content
    if isinstance(content, list):
        content = "".join(
            part.get("text", "") if isinstance(part, dict) else str(part)
            for part in content
        )
    return str(content)


def render_and_invoke(
    *,
    system_name: str,
    user_name: str,
    variables: dict[str, Any],
    mock_hint: str,
    mock_output: str,
) -> str:
    system = render_prompt(system_name, **variables)
    user = render_prompt(user_name, **variables)
    return invoke_llm(
        system=system,
        user=user,
        mock_hint=mock_hint,
        mock_output=mock_output,
    )
