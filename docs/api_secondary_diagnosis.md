# 工作流接口文档：次要诊断生成

- **workflow_id**：`secondary_diagnosis`
- **名称**：次要诊断生成
- **版本**：`8.0.0`
- **对齐来源**：Dify `【生产-V8】病案编码-02生成结果-次要诊断.yml`
- **服务默认地址**：`http://127.0.0.1:8000`
- **鉴权**：请求头 `X-API-Key`
- **可用 API Key（默认）**：`change-me-in-production`  
  （来自服务 `.env` / `.env.example` 中的 `API_KEY`；生产环境请修改后同步更新调用方）

---

## 1. 同步执行

`POST /api/v1/workflows/secondary_diagnosis/invoke`

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
  "raw_medical_record": "[{\"title\":\"出院记录\",\"content\":{\"出院诊断\":\"1.肺腺癌 2.慢性胃炎\"}}]"
}
```

**错误示例（会导致 422）**

```json
[
  {"title": "出院记录", "content": {"出院诊断": "1.肺腺癌 2.慢性胃炎"}}
]
```

### 成功响应 `200`

```json
{
  "workflow_id": "secondary_diagnosis",
  "version": "8.0.0",
  "trace_id": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
  "latency_ms": 45678,
  "result": {
    "main_diagnosis": "肺恶性肿瘤 C34.900",
    "secondary_diagnosis": "# 其他诊断：\n- 慢性胃炎 K29.500",
    "main_diagnosis_keywords": "```json\n[\"肺腺癌\",\"肺\"]\n```",
    "kb_contents": "[{\"content\":\"肺恶性肿瘤(C34.900)\"}]"
  }
}
```

### result 字段说明

| 字段 | 说明 |
|------|------|
| main_diagnosis | 规范后的主要诊断（含 ICD10） |
| secondary_diagnosis | 次要诊断 / 其他诊断结果（来自子工作流 `other_diagnosis`） |
| main_diagnosis_keywords | 主要诊断关键词提取结果 |
| kb_contents | 迭代知识库检索后汇总的 JSON 字符串 |

### 错误码

| HTTP | 说明 |
|------|------|
| 401 | 缺少或错误的 `X-API-Key` |
| 404 | workflow_id 不存在 |
| 422 | 请求体不是合法 JSON 对象 |
| 500 | 工作流执行失败；`detail.error_code=WORKFLOW_FAILED` |

---

## 2. 异步执行

`POST /api/v1/workflows/secondary_diagnosis/invoke-async`

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
  "workflow_id": "secondary_diagnosis"
}
```

### 查询任务

`GET /api/v1/tasks/{task_id}`

`status`：`queued` | `running` | `succeeded` | `failed`

成功时 `result` 结构与同步成功响应一致。

---

## 3. curl 示例（Windows）

```bash
curl -X POST http://127.0.0.1:8000/api/v1/workflows/secondary_diagnosis/invoke ^
  -H "Content-Type: application/json" ^
  -H "X-API-Key: change-me-in-production" ^
  -d @payload_invoke.json
```

`payload_invoke.json` 示例：

```json
{
  "raw_medical_record": "[...病历JSON数组字符串...]"
}
```

因链路较长（多轮 LLM + 知识库 + 子工作流），建议使用异步：

```bash
curl -X POST "http://127.0.0.1:8000/api/v1/workflows/secondary_diagnosis/invoke-async" ^
  -H "Content-Type: application/json" ^
  -H "X-API-Key: change-me-in-production" ^
  -d @payload_invoke.json
```

再轮询：

```bash
curl http://127.0.0.1:8000/api/v1/tasks/{task_id} ^
  -H "X-API-Key: change-me-in-production"
```

---

## 4. 内部依赖

### 4.1 子工作流 `other_diagnosis`

本工作流在规范主要诊断、提取出院诊断列表后，会内部调用：

- `workflow_id`：`other_diagnosis`
- 传入参数：
  - `discharge_diagnosis`：出院诊断列表 JSON 字符串
  - `main_diagnosis`：规范后的主要诊断文本

因此服务启动后必须已注册 `other_diagnosis`（默认会随包自动发现）。

### 4.2 知识库检索服务

主要诊断关键词会逐条检索知识库：

- 接口：`POST {KB_BASE_URL}/search`
- 本环境默认：`http://127.0.0.1:8090`（**不是**知识库文档默认端口 8000）
- 本工作流检索时使用 `top_k=6`

相关配置：

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| KB_BASE_URL | `http://127.0.0.1:8090` | 知识库根地址 |
| KB_CANDIDATE_K | `80` | 子向量召回条数 |
| KB_TIMEOUT_SECONDS | `30` | 超时秒数 |
| KB_ENABLED | `true` | 是否启用知识库 |

健康检查：

```bash
curl http://127.0.0.1:8090/health
```

### 4.3 LLM

依赖 `.env` 中的 `LLM_PROVIDER` / `LLM_MODEL` 等配置。

---

## 5. 处理概要

1. 并行：选择主要诊断链路 ‖ 提取出院诊断列表  
2. 按肿瘤分布类型 / 随诊 / 交搭分支提取关键词  
3. 可选食管亚部位标准化，合并检索词  
4. 迭代调用知识库，规范主要诊断  
5. 调用 `other_diagnosis` 生成次要诊断  
6. 返回主要诊断、次要诊断、关键词与知识库内容  

---

## 6. 注意事项

- 单次调用耗时通常显著长于另外两条工作流，生产环境优先异步接口。
- 知识库或子工作流失败会导致本工作流 `500` / 任务 `failed`。
- OpenAPI：`http://127.0.0.1:8000/docs`
