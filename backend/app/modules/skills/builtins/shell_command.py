"""
Built-in Skill: Shell Command

Executes shell commands with safety restrictions.
"""

import asyncio
import shlex
from pathlib import Path
from typing import Any, Dict, List, Optional
from loguru import logger


MANIFEST = {
    "name": "shell_command",
    "description": "Execute shell commands with safety restrictions",
    "version": "1.0.0",
    "author": "BRAiN Team",
    "parameters": [
        {
            "name": "command",
            "type": "string",
            "description": "Shell command to execute",
            "required": True,
        },
        {
            "name": "cwd",
            "type": "string",
            "description": "Working directory for command execution",
            "required": False,
            "default": None,
        },
        {
            "name": "timeout",
            "type": "integer",
            "description": "Command timeout in seconds",
            "required": False,
            "default": 60,
        },
        {
            "name": "env",
            "type": "object",
            "description": "Environment variables to set",
            "required": False,
            "default": {},
        },
    ],
    "returns": {
        "type": "object",
        "description": "Command output with stdout, stderr, and return code",
    },
}


async def execute(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Execute shell command.
    
    Args:
        params: Parameters including command, cwd, timeout, env
    
    Returns:
        Command output with stdout, stderr, and return code
    """
    command = params["command"]
    cwd = params.get("cwd")
    timeout = params.get("timeout", 60)
    env = params.get("env", {}) or {}
    
    logger.debug(f"🐚 Executing: {command}")
    
    # Security validation
    _validate_command(command)
    
    # Prepare working directory
    if cwd:
        cwd_path = Path(cwd).expanduser().resolve()
        if not cwd_path.exists():
            raise ValueError(f"Working directory does not exist: {cwd}")
        cwd = str(cwd_path)
    
    try:
        # Execute command
        process = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=cwd,
            env={**dict(os.environ), **env} if env else None,
        )
        
        # Wait for completion with timeout
        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=timeout
            )
        except asyncio.TimeoutError:
            process.kill()
            await process.wait()
            raise TimeoutError(f"Command timed out after {timeout} seconds")
        
        # Decode output
        stdout_str = stdout.decode("utf-8", errors="replace")
        stderr_str = stderr.decode("utf-8", errors="replace")
        
        return {
            "success": process.returncode == 0,
            "stdout": stdout_str,
            "stderr": stderr_str,
            "returncode": process.returncode,
            "command": command,
        }
        
    except Exception as e:
        logger.error(f"❌ Command execution failed: {e}")
        raise


# Forbidden commands and patterns
FORBIDDEN_COMMANDS: List[str] = [
    "rm -rf /",
    "rm -rf /*",
    "> /dev/sda",
    "mkfs",
    "dd if=/dev/zero",
    ":(){ :|:& };:",  # Fork bomb
    "chmod -R 777 /",
]

FORBIDDEN_PATTERNS: List[str] = [
    "rm -rf /",
    "rm -rf /*",
    "> /dev/sda",
    "mkfs.ext",
    "mkfs.xfs",
    "mkfs.btrfs",
]


def _validate_command(command: str) -> None:
    """
    Validate command for safety.
    
    Raises:
        PermissionError: If command contains dangerous operations
    """
    command_lower = command.lower().strip()
    
    # Check for forbidden commands
    for forbidden in FORBIDDEN_COMMANDS:
        if forbidden in command_lower:
            logger.warning(f"🚫 Blocked dangerous command: {command}")
            raise PermissionError(f"Command contains dangerous operation: {forbidden}")
    
    # Check for forbidden patterns
    for pattern in FORBIDDEN_PATTERNS:
        if pattern in command_lower:
            logger.warning(f"🚫 Blocked dangerous pattern: {command}")
            raise PermissionError(f"Command contains dangerous pattern: {pattern}")
    
    # Additional safety checks
    dangerous_patterns = [
        "sudo ",
        "su -",
    ]
    
    for pattern in dangerous_patterns:
        if pattern in command_lower:
            logger.warning(f"⚠️ Potentially dangerous command requires confirmation: {command}")
            # For now, we allow but log. In production, you might want to block or require auth.


import os
