# 工作流接口文档：其他诊断提取

- **workflow_id**：`other_diagnosis`
- **名称**：其他诊断提取
- **版本**：`1.0.0`
- **对齐来源**：Dify `【生产】病案编码-工具-其他诊断工作流.yml`
- **服务默认地址**：`http://127.0.0.1:8000`
- **鉴权**：请求头 `X-API-Key`
- **可用 API Key（默认）**：`change-me-in-production`  
  （来自服务 `.env` / `.env.example` 中的 `API_KEY`；生产环境请修改后同步更新调用方）

---

## 1. 同步执行

`POST /api/v1/workflows/other_diagnosis/invoke`

### 请求头

| 名称 | 必填 | 说明 |
|------|------|------|
| Content-Type | 是 | `application/json` |
| X-API-Key | 是 | 固定填入：`change-me-in-production` |

### 请求体

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| discharge_diagnosis | string | 是 | 出院诊断列表的 **JSON 数组字符串**，如 `["急性心肌梗死","慢性胃炎"]` |
| main_diagnosis | string | 是 | 主要诊断名称 |

**请求示例**

```json
{
  "discharge_diagnosis": "[\"急性心肌梗死\",\"高血压病3级（极高危）\",\"慢性胃炎\"]",
  "main_diagnosis": "急性心肌梗死"
}
```

说明：

- `discharge_diagnosis` 必须是字符串，内容是 JSON 数组文本，而不是 JSON 数组本身。
- 工作流会排除主要诊断，对其余诊断检索 ICD10 并输出“其他诊断”。

### 成功响应 `200`

```json
{
  "workflow_id": "other_diagnosis",
  "version": "1.0.0",
  "trace_id": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
  "latency_ms": 3200,
  "result": {
    "other_diagnosis": "# 其他诊断：\n- 高血压病3级（极高危）I10.x00x032\n- 慢性胃炎 K29.500"
  }
}
```

### result 字段说明

| 字段 | 说明 |
|------|------|
| other_diagnosis | 其他诊断结果（通常为 Markdown 文本，含 ICD10 名称与编码） |

### 错误码

| HTTP | 说明 |
|------|------|
| 401 | 缺少或错误的 `X-API-Key` |
| 404 | workflow_id 不存在 |
| 422 | 请求体不是合法 JSON 对象 |
| 500 | 工作流执行失败；`detail.error_code=WORKFLOW_FAILED` |

---

## 2. 异步执行

`POST /api/v1/workflows/other_diagnosis/invoke-async`

### 请求体

与同步接口相同，可额外携带：

| 字段/参数 | 位置 | 说明 |
|-----------|------|------|
| callback_url | Query 或 Body | 可选。任务完成后回调 |

### 成功响应 `200`

```json
{
  "task_id": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
  "status": "queued",
  "workflow_id": "other_diagnosis"
}
```

### 查询任务

`GET /api/v1/tasks/{task_id}`

`status`：`queued` | `running` | `succeeded` | `failed`

成功时 `result` 结构与同步成功响应一致。

---

## 3. curl 示例（Windows）

```bash
curl -X POST http://127.0.0.1:8000/api/v1/workflows/other_diagnosis/invoke ^
  -H "Content-Type: application/json" ^
  -H "X-API-Key: change-me-in-production" ^
  -d "{\"discharge_diagnosis\": \"[\\\"急性心肌梗死\\\",\\\"慢性胃炎\\\"]\", \"main_diagnosis\": \"急性心肌梗死\"}"
```

---

## 4. 外部依赖：知识库检索服务

本工作流会对出院诊断列表 **逐条** 调用知识库：

- 接口：`POST {KB_BASE_URL}/search`
- 本环境默认：`http://127.0.0.1:8090`（**不是**知识库文档中的默认端口 8000）
- 相关配置（服务 `.env`）：

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| KB_BASE_URL | `http://127.0.0.1:8090` | 知识库根地址 |
| KB_TOP_K | `4` | 返回诊断码条数 |
| KB_CANDIDATE_K | `80` | 子向量召回条数 |
| KB_TIMEOUT_SECONDS | `30` | 超时秒数 |
| KB_ENABLED | `true` | 是否启用知识库 |

知识库请求体示例：

```json
{
  "query": "慢性胃炎",
  "top_k": 4,
  "candidate_k": 80
}
```

调用前请确认知识库服务已在 `127.0.0.1:8090` 启动，可用：

```bash
curl http://127.0.0.1:8090/health
```

---

## 5. 注意事项

- 同时依赖 LLM 与知识库；知识库不可用时检索结果可能为空，模型仍可能输出“未找到编码”类结果。
- 本工作流也会被 `secondary_diagnosis` 作为子工作流内部调用。
- OpenAPI：`http://127.0.0.1:8000/docs`
