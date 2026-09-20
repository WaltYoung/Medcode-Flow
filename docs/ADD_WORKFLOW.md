# 新增工作流 Checklist

新增第 N 条工作流时，**不要改 API 路由**。复制 `_template` 并完成下列步骤即可被自动发现。

1. 复制目录 `app/workflows/_template` 为 `app/workflows/<your_id>/`（目录名不要以下划线开头）。
2. 填写 `WORKFLOW_ID`、`VERSION`、`name`、`description`。
3. 在 `state.py` 定义图状态；在 `schemas.py` 定义请求/响应模型。
4. 在 `graph.py` 用 LangGraph 声明节点与边；复杂 Prompt 放到 `prompts/`。
5. 在 `__init__.py` 调用 `registry.register(WorkflowSpec(...))`。
6. 增加 `tests/test_<your_id>.py`：mock LLM 下编译图并能 `invoke`。
7. 重启 API / Worker 后，`GET /api/v1/workflows` 应出现新 id。

约定：

- `workflow_id` 使用 snake_case，与包名一致。
- 节点只通过 `LLMFactory` 取模型，禁止在节点里写死厂商 SDK。
- Dify YAML 仅作对照，不在运行时解析。
