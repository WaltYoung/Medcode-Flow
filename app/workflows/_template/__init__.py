from __future__ import annotations

from app.runtime.registry import WorkflowSpec, registry
from app.workflows._template.graph import build_graph
from app.workflows._template.schemas import TemplateRequest, TemplateResult

# 复制本包后改为真实 id，并删除包名的下划线前缀，才会被自动发现。
WORKFLOW_ID = "template_echo"
VERSION = "0.1.0"


def _input_mapper(request: TemplateRequest) -> dict:
    return {"text": request.text}


def _output_mapper(state: dict) -> TemplateResult:
    return TemplateResult(echo=state.get("echo") or "")


def register() -> None:
    registry.register(
        WorkflowSpec(
            workflow_id=WORKFLOW_ID,
            name="模板回声工作流",
            version=VERSION,
            description="复制此包后改名即可扩展新工作流",
            build_graph=build_graph,
            request_model=TemplateRequest,
            response_model=TemplateResult,
            input_mapper=_input_mapper,
            output_mapper=_output_mapper,
        )
    )


# 模板包以下划线开头，discover_workflows 不会 import 本模块。
# 复制为正式包后取消下一行注释（或在包被 import 时自动执行）。
# register()
