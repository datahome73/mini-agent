"""
Web 工具 — 网页抓取和搜索。
"""

import json
import logging

import httpx

from tools.base import Tool

logger = logging.getLogger(__name__)

# 简单的用户代理，避免被拒绝
HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; MiniAgent/1.0)"
}


async def web_fetch(url: str) -> str:
    """获取网页内容并转为文本"""
    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=15.0) as client:
            resp = await client.get(url, headers=HEADERS)
            resp.raise_for_status()
            text = resp.text

            # 简易的 HTML → 文本提取
            import re
            text = re.sub(r"<script[^>]*>.*?</script>", "", text, flags=re.DOTALL)
            text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.DOTALL)
            text = re.sub(r"<[^>]+>", " ", text)
            text = re.sub(r"\s+", " ", text).strip()
            if len(text) > 5000:
                text = text[:5000] + "\n\n... (内容已截断)"
            return text
    except httpx.TimeoutException:
        return "错误：请求超时"
    except Exception as e:
        return f"错误：抓取失败 — {e}"


async def web_search(query: str) -> str:
    """
    简单的 web 搜索 — 使用 DuckDuckGo 的 lite 接口（无需 API Key）。
    注意：此接口非官方，仅供学习研究使用。
    """
    try:
        url = "https://lite.duckduckgo.com/lite/"
        async with httpx.AsyncClient(follow_redirects=True, timeout=10.0) as client:
            resp = await client.post(url, data={"q": query}, headers=HEADERS)
            resp.raise_for_status()
            text = resp.text

            import re
            # 粗略提取结果链接和标题
            results = re.findall(
                r'<a[^>]*href="(https?://[^"]+)"[^>]*>(.*?)</a>',
                text,
                re.DOTALL,
            )
            lines = []
            for href, title in results[:8]:
                title = re.sub(r"<[^>]+>", "", title).strip()
                if title:
                    lines.append(f"- [{title}]({href})")
            if not lines:
                return "未找到搜索结果"
            return "\n".join(lines)
    except Exception as e:
        return f"搜索失败：{e}"


# ===== 注册 =====
web_fetch_tool = Tool(
    name="web_fetch",
    description="抓取指定 URL 的网页内容并转为纯文本。用于阅读在线文档、文章。",
    parameters={
        "type": "object",
        "properties": {
            "url": {"type": "string", "description": "要抓取的 URL"},
        },
        "required": ["url"],
    },
    fn=web_fetch,
)

web_search_tool = Tool(
    name="web_search",
    description="搜索互联网，返回相关链接列表。用于获取最新信息。",
    parameters={
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "搜索关键词"},
        },
        "required": ["query"],
    },
    fn=web_search,
)
