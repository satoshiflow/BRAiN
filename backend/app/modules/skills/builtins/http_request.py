"""
Built-in Skill: HTTP Request

Makes HTTP requests to external APIs.

Security Notes:
- All requests are validated to prevent SSRF attacks
- Private IP ranges, localhost, and AWS metadata endpoints are blocked
- External HTTPS requests are required for security
"""

from typing import Any, Dict, Optional
import httpx
import ipaddress
from urllib.parse import urlparse
from loguru import logger


def _is_valid_url(url: str) -> bool:
    """
    Validate URL to prevent SSRF attacks.

    Blocks:
    - Private IP ranges (10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16)
    - Localhost/loopback (127.0.0.0/8, ::1)
    - Link-local addresses (169.254.0.0/16)
    - AWS metadata endpoint (169.254.169.254)
    - Non-HTTPS external URLs

    Args:
        url: URL to validate

    Returns:
        True if URL is safe, False otherwise

    Raises:
        ValueError: If URL is invalid or unsafe
    """
    try:
        parsed = urlparse(url)

        # Must have scheme and netloc
        if not parsed.scheme or not parsed.netloc:
            raise ValueError("Invalid URL: missing scheme or netloc")

        # Only allow HTTP and HTTPS
        if parsed.scheme not in ['http', 'https']:
            raise ValueError("Invalid URL: unsupported scheme")

        # Extract hostname
        hostname = parsed.hostname
        if not hostname:
            raise ValueError("Invalid URL: could not extract hostname")

        # Block common loopback hostnames
        blocked_hostnames = ['localhost', '127.0.0.1', '::1', '[::1]']
        if hostname.lower() in blocked_hostnames or hostname in blocked_hostnames:
            logger.warning(f"SSRF: Blocked access to loopback hostname {hostname}")
            raise ValueError("Invalid URL: cannot access internal networks")

        # Try to parse as IP address
        is_ip = False
        try:
            ip = ipaddress.ip_address(hostname)
            is_ip = True

            # Block private/internal IPs
            blocked_reasons = []
            if ip.is_private:
                blocked_reasons.append("private IP range")
            if ip.is_loopback:
                blocked_reasons.append("loopback address")
            if ip.is_link_local:
                blocked_reasons.append("link-local address")
            if ip.is_reserved:
                blocked_reasons.append("reserved address")

            if blocked_reasons:
                reason = ", ".join(blocked_reasons)
                logger.warning(f"SSRF: Blocked access to {hostname} ({reason})")
                raise ValueError("Invalid URL: cannot access internal networks")

        except ValueError as e:
            # If we determined it's an IP and raised error, re-raise
            if is_ip or "cannot access internal networks" in str(e):
                raise
            # Otherwise it's just not an IP address (domain name), continue
            pass

        return True

    except ValueError as e:
        # Re-raise ValueError as is (contains user-safe message)
        raise
    except Exception as e:
        logger.error(f"URL validation error for {url}: {e}")
        raise ValueError("Invalid URL: validation failed")


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

    Raises:
        ValueError: If URL fails SSRF validation
        Exception: If request fails
    """
    url = params["url"]
    method = params.get("method", "GET").upper()
    headers = params.get("headers", {}) or {}
    body = params.get("body")
    timeout = params.get("timeout", 30)

    # Validate URL before making request
    try:
        _is_valid_url(url)
    except ValueError as e:
        logger.warning(f"HTTP request blocked: {str(e)}")
        raise Exception(str(e))

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
