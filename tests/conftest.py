import json
import os

os.environ["LLM_PROVIDER"] = "mock"
os.environ["REDIS_URL"] = "memory://"
os.environ["API_KEY"] = "test-key"
os.environ["APP_ENV"] = "test"

from app.core.config import get_settings
from app.core.llm import get_llm_factory

get_settings.cache_clear()
get_llm_factory.__globals__["_factory"] = None

SAMPLE_RECORD = [
    {
        "title": "出院记录",
        "content": {
            "入院日期": "2024-01-01",
            "出院日期": "2024-01-10",
            "治疗经过": "行化疗一程",
        },
    },
    {
        "title": "入院记录",
        "content": {
            "主诉": "发现肺部占位",
            "现病史": "患者既往肺癌病史",
            "既往史": "高血压",
            "手术外伤史": "无",
            "入院日期": "2024-01-01",
        },
    },
    {
        "title": "临时医嘱单",
        "content": {
            "医嘱内容": "<table><tr><th>医嘱</th><th>时间</th></tr><tr><td>化疗</td><td>2024-01-02</td></tr></table>"
        },
    },
]


def sample_record_json() -> str:
    return json.dumps(SAMPLE_RECORD, ensure_ascii=False)
