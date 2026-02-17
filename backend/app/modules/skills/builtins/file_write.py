"""
Built-in Skill: File Write

Writes content to files on the filesystem.
"""

from pathlib import Path
from typing import Any, Dict
from loguru import logger


MANIFEST = {
    "name": "file_write",
    "description": "Write content to files on the filesystem",
    "version": "1.0.0",
    "author": "BRAiN Team",
    "parameters": [
        {
            "name": "path",
            "type": "string",
            "description": "Path to the file to write",
            "required": True,
        },
        {
            "name": "content",
            "type": "string",
            "description": "Content to write to the file",
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
            "name": "append",
            "type": "boolean",
            "description": "Append to file instead of overwriting",
            "required": False,
            "default": False,
        },
        {
            "name": "create_dirs",
            "type": "boolean",
            "description": "Create parent directories if they don't exist",
            "required": False,
            "default": True,
        },
    ],
    "returns": {
        "type": "object",
        "description": "Write result with bytes written",
    },
}


def execute(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Execute file write.
    
    Args:
        params: Parameters including path, content, encoding, append, create_dirs
    
    Returns:
        Write result with bytes written
    """
    file_path = params["path"]
    content = params["content"]
    encoding = params.get("encoding", "utf-8")
    append = params.get("append", False)
    create_dirs = params.get("create_dirs", True)
    
    # Convert to Path object
    path = Path(file_path).expanduser()
    
    logger.debug(f"✏️ Writing file: {path}")
    
    # Security check
    _security_check(path)
    
    # Create parent directories if needed
    if create_dirs:
        path.parent.mkdir(parents=True, exist_ok=True)
    
    # Determine write mode
    mode = "a" if append else "w"
    
    # Write file
    bytes_written = path.write_text(content, encoding=encoding)
    
    return {
        "success": True,
        "path": str(path.resolve()),
        "bytes_written": bytes_written,
        "mode": "append" if append else "write",
        "encoding": encoding,
    }


def _security_check(path: Path) -> None:
    """
    Security check to prevent writing to sensitive locations.
    
    Raises:
        PermissionError: If path is in a restricted location
    """
    # List of forbidden paths/patterns
    forbidden_patterns = [
        "/etc",
        "/usr/bin",
        "/bin",
        "/sbin",
        "/boot",
        ".ssh",
        ".aws",
    ]
    
    path_str = str(path).lower()
    
    for forbidden in forbidden_patterns:
        if path_str.startswith(forbidden) or forbidden in path_str:
            logger.warning(f"🚫 Attempted to write to restricted location: {path}")
            raise PermissionError(f"Access denied to restricted location: {path}")
