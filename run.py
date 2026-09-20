"""打包/本地启动入口：启动 FastAPI 工作流服务。"""

from __future__ import annotations

import uvicorn

from app.main import app


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
