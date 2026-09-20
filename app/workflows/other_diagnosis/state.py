from __future__ import annotations

from typing import Any, TypedDict


class OtherDiagnosisState(TypedDict, total=False):
    discharge_diagnosis: str
    main_diagnosis: str
    cyzd_list: list[str]
    kb_context: str
    iteration_output: list[dict[str, Any]]
    other_diagnosis: str
