# LangGraph 企业工作流服务

将 Dify 生产工作流手工复刻为 LangGraph，通过 FastAPI 提供同步/异步接口。首条工作流：`medical_record_extract`（对齐 `reference/【生产-V8】01 病历信息提取.yml`）。

## 快速开始

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```

本地默认 `LLM_PROVIDER=mock`，无需真实模型即可跑通拓扑。

```bash
# 仅同步调试可用 memory 队列
set REDIS_URL=memory://
set LLM_PROVIDER=mock
uvicorn app.main:app --reload --port 8000
```

异步任务需要 Redis + Worker：

```bash
docker compose up --build
```

## API

鉴权头：`X-API-Key`（与 `.env` 中 `API_KEY` 一致）

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/v1/health` | 探活 |
| GET | `/api/v1/workflows` | 已注册工作流 |
| POST | `/api/v1/workflows/{id}/invoke` | 同步执行 |
| POST | `/api/v1/workflows/{id}/invoke-async` | 入队，返回 `task_id` |
| GET | `/api/v1/tasks/{task_id}` | 查询任务状态 |

已注册工作流：

| workflow_id | 说明 |
|---|---|
| `medical_record_extract` | 病历信息提取（Dify V8） |
| `other_diagnosis` | 其他诊断提取（依赖知识库 `KB_BASE_URL`，默认 `http://127.0.0.1:8090`） |
| `secondary_diagnosis` | 次要诊断生成（Dify V8；内部调用 `other_diagnosis` + 知识库 8090） |

同步调用示例：

```bash
curl -X POST http://127.0.0.1:8000/api/v1/workflows/medical_record_extract/invoke ^
  -H "Content-Type: application/json" ^
  -H "X-API-Key: change-me-in-production" ^
  -d "{\"raw_medical_record\": \"[{\\\"title\\\":\\\"入院记录\\\",\\\"content\\\":{\\\"主诉\\\":\\\"咳嗽\\\"}}]\"}"
```

其他诊断示例：

```bash
curl -X POST http://127.0.0.1:8000/api/v1/workflows/other_diagnosis/invoke ^
  -H "Content-Type: application/json" ^
  -H "X-API-Key: change-me-in-production" ^
  -d "{\"discharge_diagnosis\": \"[\\\"急性心肌梗死\\\",\\\"慢性胃炎\\\"]\", \"main_diagnosis\": \"急性心肌梗死\"}"
```

次要诊断示例（输入原始病历，内部会再调 `other_diagnosis`）：

```bash
curl -X POST http://127.0.0.1:8000/api/v1/workflows/secondary_diagnosis/invoke ^
  -H "Content-Type: application/json" ^
  -H "X-API-Key: change-me-in-production" ^
  -d @payload_invoke.json
```
## 知识库依赖

`other_diagnosis` 会调用智能病案编码检索服务：

- 接口：`POST {KB_BASE_URL}/search`
- 本环境默认：`http://127.0.0.1:8090`（注意不是文档里的 8000）
- 可在 `.env` 调整 `KB_BASE_URL` / `KB_TOP_K` / `KB_CANDIDATE_K`
## LLM 切换

`.env`：

```env
# dashscope | openai_compatible | hospital | mock
LLM_PROVIDER=dashscope
LLM_MODEL=qwen3-32b
DASHSCOPE_API_KEY=sk-xxx

# 或内网 OpenAI 兼容网关
LLM_PROVIDER=openai_compatible
OPENAI_API_KEY=sk-xxx
OPENAI_BASE_URL=http://your-gateway:8000/v1

# 或医院内部算力（鉴权头 X-API-KEY，模型默认 Qwen3-32B）
LLM_PROVIDER=hospital
HOSPITAL_LLM_BASE_URL=http://172.28.24.104:30020/endpoint/AFTYb_g8w89_28ZWS/v1
HOSPITAL_LLM_API_KEY=0fdc3ad71bfb5a97989a2efdf959d7e7
HOSPITAL_LLM_MODEL=Qwen3-32B
```

## 新增一条工作流

见 [docs/ADD_WORKFLOW.md](docs/ADD_WORKFLOW.md)，可复制 [app/workflows/_template](app/workflows/_template)。

## 测试

```bash
set LLM_PROVIDER=mock
set REDIS_URL=memory://
set API_KEY=test-key
pytest -q
```
