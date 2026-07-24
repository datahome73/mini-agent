"""
HTTP 请求工具 — 通用 HTTP 客户端，支持 GET/POST/PUT/DELETE。
补齐 web_fetch（只 GET 纯文本）的不足，用于调用 API。
"""

import json as json_lib
import logging

import httpx

from tools.base import Tool

logger = logging.getLogger(__name__)

_RESULT_MAX = 6000  # 返回值截断长度


async def http_request(
    method: str = "GET",
    url: str = "",
    headers: dict | None = None,
    body: str = "",
    body_type: str = "json",
) -> str:
    """发送 HTTP 请求"""
    if not url:
        return "错误：url 不能为空"

    method = method.upper()
    if method not in ("GET", "POST", "PUT", "DELETE", "PATCH"):
        return f"错误：不支持的 method '{method}'，支持 GET/POST/PUT/DELETE/PATCH"

    # 构造请求头
    req_headers = {
        "User-Agent": "MiniAgent/1.0",
    }
    if headers:
        # 用户传入的 headers 覆盖默认
        req_headers.update({str(k): str(v) for k, v in headers.items()})

    # 构造请求体
    req_body = None
    if body and method in ("POST", "PUT", "PATCH"):
        if body_type == "json":
            req_body = body
            if "Content-Type" not in {k.lower() for k in req_headers}:
                req_headers["Content-Type"] = "application/json"
        else:
            req_body = body

    try:
        async with httpx.AsyncClient(
            follow_redirects=True, timeout=30.0,
        ) as client:
            resp = await client.request(
                method=method,
                url=url,
                headers=req_headers,
                content=req_body,
            )

        # 尝试解析响应
        content_type = resp.headers.get("content-type", "")
        body_text = resp.text

        # 如果返回 JSON，格式化输出
        if "json" in content_type and body_text:
            try:
                parsed = json_lib.loads(body_text)
                body_text = json_lib.dumps(parsed, ensure_ascii=False, indent=2)
            except json_lib.JSONDecodeError:
                pass

        # 截断
        if len(body_text) > _RESULT_MAX:
            body_text = body_text[:_RESULT_MAX] + "\n\n... (响应已截断)"

        return (
            f"状态码: {resp.status_code}\n"
            f"请求: {method} {url}\n"
            f"响应体:\n{body_text}"
        )

    except httpx.TimeoutException:
        return f"错误：请求超时 — {method} {url}"
    except httpx.HTTPStatusError as e:
        return f"错误：HTTP {e.response.status_code} — {method} {url}\n响应体:\n{e.response.text[:_RESULT_MAX]}"
    except Exception as e:
        return f"错误：请求失败 — {e}"


# ===== 注册 =====

http_request_tool = Tool(
    name="http_request",
    description=(
        "发送 HTTP 请求，支持 GET/POST/PUT/DELETE/PATCH。"
        "可自定义请求头和请求体，支持 JSON 和纯文本格式。"
        "用于调用 REST API、提交数据、身份认证等场景。"
        "注意：读取普通网页内容请用 web_fetch（自动转纯文本）。"
    ),
    parameters={
        "type": "object",
        "properties": {
            "method": {
                "type": "string",
                "enum": ["GET", "POST", "PUT", "DELETE", "PATCH"],
                "description": "HTTP 方法（默认 GET）",
            },
            "url": {
                "type": "string",
                "description": "请求 URL",
            },
            "headers": {
                "type": "object",
                "description": "自定义请求头，如 {\"Authorization\": \"Bearer sk-xxx\"}",
            },
            "body": {
                "type": "string",
                "description": "请求体内容（JSON 字符串或纯文本）",
            },
            "body_type": {
                "type": "string",
                "enum": ["json", "text"],
                "description": "body 格式：json（自动设 Content-Type）或 text",
            },
        },
        "required": ["method", "url"],
    },
    fn=http_request,
    requires_confirmation=lambda args: args.get("method", "GET") in ("POST", "PUT", "DELETE", "PATCH"),
)
