# 工作流接口文档：病历信息提取

- **workflow_id**：`medical_record_extract`
- **名称**：病历信息提取
- **版本**：`8.0.0`
- **对齐来源**：Dify `【生产-V8】01 病历信息提取.yml`
- **服务默认地址**：`http://127.0.0.1:8000`
- **鉴权**：请求头 `X-API-Key`
- **可用 API Key（默认）**：`change-me-in-production`  
  （来自服务 `.env` / `.env.example` 中的 `API_KEY`；生产环境请修改后同步更新调用方）

---

## 1. 同步执行

`POST /api/v1/workflows/medical_record_extract/invoke`

### 请求头

| 名称 | 必填 | 说明 |
|------|------|------|
| Content-Type | 是 | `application/json` |
| X-API-Key | 是 | 固定填入：`change-me-in-production` |

### 请求体

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| raw_medical_record | string | 是 | 原始病历文本。须为 **JSON 数组再序列化后的字符串**（根节点是字符串，不是数组） |

**正确示例**

```json
{
  "raw_medical_record": "[{\"title\":\"入院记录\",\"content\":{\"主诉\":\"咳嗽\"}}]"
}
```

**错误示例（会导致 422）**

```json
[
  {"title": "入院记录", "content": {"主诉": "咳嗽"}}
]
```

说明：HTTP Body 根节点必须是对象；病历数组需先 `json.dumps` 后放入 `raw_medical_record`。

### 成功响应 `200`

```json
{
  "workflow_id": "medical_record_extract",
  "version": "8.0.0",
  "trace_id": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
  "latency_ms": 12345,
  "result": {
    "medical_summary": "病历摘要文本",
    "has_history_diagnosis": "是否存在历史确诊",
    "is_first_antitumor": "是否首次抗肿瘤治疗",
    "abandon_original_plan": "是否拟放弃原治疗计划",
    "malignant_location": "肿瘤位置",
    "diagnosis_list": "诊断清单",
    "treatment_methods": "治疗方式"
  }
}
```

### result 字段说明

| 字段 | 说明 |
|------|------|
| medical_summary | 病历摘要（初始化提取） |
| has_history_diagnosis | 是否存在历史确诊 |
| is_first_antitumor | 是否首次抗肿瘤治疗 |
| abandon_original_plan | 是否拟放弃原治疗计划（无治疗经过时可能为空） |
| malignant_location | 肿瘤位置相关结论 |
| diagnosis_list | 诊断清单 |
| treatment_methods | 治疗方式 |

### 错误码

| HTTP | 说明 |
|------|------|
| 401 | 缺少或错误的 `X-API-Key` |
| 404 | workflow_id 不存在 |
| 422 | 请求体不是合法 JSON 对象 |
| 500 | 工作流执行失败；`detail.error_code=WORKFLOW_FAILED` |

---

## 2. 异步执行

`POST /api/v1/workflows/medical_record_extract/invoke-async`

### 请求体

与同步接口相同，可额外携带：

| 字段/参数 | 位置 | 说明 |
|-----------|------|------|
| callback_url | Query 或 Body | 可选。任务完成后向该 URL `POST` 任务结果 |

### 成功响应 `200`

```json
{
  "task_id": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
  "status": "queued",
  "workflow_id": "medical_record_extract"
}
```

### 查询任务

`GET /api/v1/tasks/{task_id}`

```json
{
  "task_id": "...",
  "workflow_id": "medical_record_extract",
  "status": "succeeded",
  "result": { "...同步成功响应结构..." },
  "error": null
}
```

`status`：`queued` | `running` | `succeeded` | `failed`

---

## 3. curl 示例（Windows）

```bash
curl -X POST http://127.0.0.1:8000/api/v1/workflows/medical_record_extract/invoke ^
  -H "Content-Type: application/json" ^
  -H "X-API-Key: change-me-in-production" ^
  -d @payload_invoke.json
```

其中 `payload_invoke.json` 结构为：

```json
{
  "raw_medical_record": "[...病历JSON数组字符串...]"
}
```

---

## 4. 依赖与注意事项

- 依赖 LLM（`.env`：`LLM_PROVIDER` / `LLM_MODEL` 等），不依赖知识库服务。
- 单次调用含多次串/并行 LLM，耗时可能较长；生产建议优先异步接口，并调高客户端超时。
- OpenAPI：`http://127.0.0.1:8000/docs`
