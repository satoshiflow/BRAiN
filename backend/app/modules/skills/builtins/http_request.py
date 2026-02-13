"""
Built-in Skill: HTTP Request

Makes HTTP requests to external APIs.
"""

from typing import Any, Dict, Optional
import httpx
from loguru import logger


MANIFEST = {
    "name": "http_request",
    "description": "Make HTTP requests to external APIs",
    "version": "1.0.0",
    "author": "BRAiN Team",
    "parameters": [
        {
            "name": "url",
            "type": "string",
            "description": "The URL to request",
            "required": True,
        },
        {
            "name": "method",
            "type": "string",
            "description": "HTTP method (GET, POST, PUT, DELETE, PATCH)",
            "required": False,
            "default": "GET",
        },
        {
            "name": "headers",
            "type": "object",
            "description": "Request headers as key-value pairs",
            "required": False,
            "default": {},
        },
        {
            "name": "body",
            "type": "object",
            "description": "Request body for POST/PUT/PATCH requests",
            "required": False,
            "default": None,
        },
        {
            "name": "timeout",
            "type": "integer",
            "description": "Request timeout in seconds",
            "required": False,
            "default": 30,
        },
    ],
    "returns": {
        "type": "object",
        "description": "Response with status, headers, and body",
    },
}


async def execute(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Execute HTTP request.
    
    Args:
        params: Parameters including url, method, headers, body, timeout
    
    Returns:
        Response data with status_code, headers, and body
    """
    url = params["url"]
    method = params.get("method", "GET").upper()
    headers = params.get("headers", {}) or {}
    body = params.get("body")
    timeout = params.get("timeout", 30)
    
    logger.debug(f"🌐 HTTP {method} {url}")
    
    async with httpx.AsyncClient(timeout=timeout) as client:
        try:
            if method == "GET":
                response = await client.get(url, headers=headers)
            elif method == "POST":
                response = await client.post(url, headers=headers, json=body)
            elif method == "PUT":
                response = await client.put(url, headers=headers, json=body)
            elif method == "DELETE":
                response = await client.delete(url, headers=headers)
            elif method == "PATCH":
                response = await client.patch(url, headers=headers, json=body)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
            
            # Try to parse JSON response
            try:
                response_body = response.json()
            except Exception:
                response_body = response.text
            
            return {
                "success": True,
                "status_code": response.status_code,
                "headers": dict(response.headers),
                "body": response_body,
                "url": str(response.url),
            }
            
        except httpx.TimeoutException:
            logger.error(f"⏱️ Request timeout: {url}")
            raise Exception(f"Request timed out after {timeout} seconds")
        except httpx.RequestError as e:
            logger.error(f"❌ Request failed: {e}")
            raise Exception(f"Request failed: {e}")
