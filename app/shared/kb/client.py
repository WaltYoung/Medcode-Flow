from __future__ import annotations

import logging
from typing import Any

import httpx

from app.core.config import Settings, get_settings

logger = logging.getLogger(__name__)


class KnowledgeBaseClient:
    """智能病案编码检索服务客户端（POST /search）。"""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    @property
    def base_url(self) -> str:
        return self.settings.kb_base_url.rstrip("/")

    def search(
        self,
        query: str,
        *,
        top_k: int | None = None,
        candidate_k: int | None = None,
    ) -> list[dict[str, Any]]:
        if not self.settings.kb_enabled:
            logger.warning("kb_disabled query=%s", query)
            return []

        payload = {
            "query": query,
            "top_k": top_k if top_k is not None else self.settings.kb_top_k,
            "candidate_k": (
                candidate_k
                if candidate_k is not None
                else self.settings.kb_candidate_k
            ),
        }
        url = f"{self.base_url}/search"
        try:
            with httpx.Client(timeout=self.settings.kb_timeout_seconds) as client:
                resp = client.post(url, json=payload)
                resp.raise_for_status()
                data = resp.json()
        except Exception:
            logger.exception("kb_search_failed url=%s query=%s", url, query)
            raise

        results = data.get("results") or []
        if not isinstance(results, list):
            raise ValueError(f"Unexpected KB response: results is {type(results)}")
        return results

    def health(self) -> dict[str, Any]:
        url = f"{self.base_url}/health"
        with httpx.Client(timeout=self.settings.kb_timeout_seconds) as client:
            resp = client.get(url)
            resp.raise_for_status()
            return resp.json()


def search_results_to_knowledges(
    results: list[dict[str, Any]],
) -> list[dict[str, str]]:
    """将本地检索结果转为接近 Dify knowledge-retrieval 的 content 结构。"""
    knowledges: list[dict[str, str]] = []
    for row in results:
        name = str(row.get("diag_name") or "").strip()
        code = str(row.get("diag_code") or "").strip()
        evidence = str(row.get("evidence") or "").strip()
        lines = []
        if name and code:
            lines.append(f"{name}({code})")
        elif name:
            lines.append(name)
        elif code:
            lines.append(code)
        if evidence and evidence not in lines:
            lines.append(evidence)
        matched = row.get("matched_keywords") or []
        if isinstance(matched, list):
            for kw in matched:
                if isinstance(kw, dict):
                    text = str(kw.get("kw_text") or "").strip()
                else:
                    text = str(kw).strip()
                if text and text not in lines:
                    lines.append(text)
        if lines:
            knowledges.append({"content": "\n".join(lines)})
    return knowledges


_client: KnowledgeBaseClient | None = None


def get_kb_client() -> KnowledgeBaseClient:
    global _client
    if _client is None:
        _client = KnowledgeBaseClient()
    return _client
