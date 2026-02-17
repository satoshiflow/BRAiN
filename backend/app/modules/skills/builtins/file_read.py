"""
Built-in Skill: File Read

Reads file contents from the filesystem.
"""

import os
from pathlib import Path
from typing import Any, Dict
from loguru import logger


MANIFEST = {
    "name": "file_read",
    "description": "Read file contents from the filesystem",
    "version": "1.0.0",
    "author": "BRAiN Team",
    "parameters": [
        {
            "name": "path",
            "type": "string",
            "description": "Path to the file to read",
            "required": True,
        },
        {
            "name": "encoding",
            "type": "string",
            "description": "File encoding (default: utf-8)",
            "required": False,
            "default": "utf-8",
        },
        {
            "name": "limit",
            "type": "integer",
            "description": "Maximum number of bytes/lines to read",
            "required": False,
            "default": None,
        },
    ],
    "returns": {
        "type": "object",
        "description": "File contents and metadata",
    },
}


def execute(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Execute file read.
    
    Args:
        params: Parameters including path, encoding, limit
    
    Returns:
        File contents and metadata
    """
    file_path = params["path"]
    encoding = params.get("encoding", "utf-8")
    limit = params.get("limit")
    
    # Convert to Path object and resolve
    path = Path(file_path).expanduser().resolve()
    
    logger.debug(f"📖 Reading file: {path}")
    
    # Security check - prevent reading sensitive files
    _security_check(path)
    
    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")
    
    if not path.is_file():
        raise ValueError(f"Path is not a file: {file_path}")
    
    # Check file size
    file_size = path.stat().st_size
    max_size = 10 * 1024 * 1024  # 10 MB limit
    
    if file_size > max_size:
        raise ValueError(f"File too large ({file_size} bytes). Maximum allowed: {max_size} bytes")
    
    # Read file
    try:
        content = path.read_text(encoding=encoding)
        
        # Apply limit if specified
        if limit and isinstance(limit, int):
            content = content[:limit]
        
        return {
            "success": True,
            "path": str(path),
            "content": content,
            "size": len(content),
            "encoding": encoding,
        }
    except UnicodeDecodeError:
        # Try binary read for non-text files
        binary_content = path.read_bytes()
        if limit and isinstance(limit, int):
            binary_content = binary_content[:limit]
        
        return {
            "success": True,
            "path": str(path),
            "content": binary_content.hex(),
            "size": len(binary_content),
            "encoding": "binary",
            "note": "File read as binary (hex encoded)",
        }


def _security_check(path: Path) -> None:
    """
    Security check to prevent reading sensitive system files.
    
    Raises:
        PermissionError: If file is in a restricted location
    """
    # List of forbidden paths
    forbidden_prefixes = [
        "/etc/shadow",
        "/etc/passwd",
        "/etc/ssh",
        ".ssh/id_",
        ".env",
        ".aws/credentials",
        ".docker/config.json",
    ]
    
    path_str = str(path).lower()
    
    for forbidden in forbidden_prefixes:
        if forbidden in path_str:
            logger.warning(f"🚫 Attempted to read restricted file: {path}")
            raise PermissionError(f"Access denied to restricted file: {path}")
