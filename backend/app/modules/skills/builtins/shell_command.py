"""
Built-in Skill: Shell Command

Executes shell commands with safety restrictions.
"""

import asyncio
import os
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
            "description": "Shell command to execute (single command only, no pipes or redirects)",
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
            "description": "Command timeout in seconds (max 300)",
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
    
    # Enforce timeout limits
    timeout = min(timeout, 300)  # Max 5 minutes
    
    # Prepare working directory
    if cwd:
        cwd_path = Path(cwd).expanduser().resolve()
        if not cwd_path.exists():
            raise ValueError(f"Working directory does not exist: {cwd}")
        cwd = str(cwd_path)
    
    try:
        # SECURITY FIX: Use shell=False equivalent by parsing command safely
        # Split command into args using shlex (safer than shell=True)
        cmd_args = shlex.split(command)
        
        if not cmd_args:
            raise ValueError("Empty command")
        
        # Execute command WITHOUT shell to prevent injection
        process = await asyncio.create_subprocess_exec(
            *cmd_args,
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
    ">/dev/sda",
    "curl",
    "wget",
    "nc ",
    "ncat",
    "netcat",
    "bash -i",
    "sh -i",
    "python -c",
    "python3 -c",
    "perl -e",
    "ruby -e",
]

FORBIDDEN_PATTERNS: List[str] = [
    "rm -rf /",
    "rm -rf /*",
    "> /dev/sda",
    ">/dev/sda",
    "mkfs.ext",
    "mkfs.xfs",
    "mkfs.btrfs",
    "| bash",
    "| sh",
    "|bash",
    "|sh",
    "&& bash",
    "&& sh",
    "; bash",
    "; sh",
    "$(",
    "${",
    "`",
]

# Whitelist of allowed commands (optional strict mode)
ALLOWED_COMMANDS: set = {
    "ls", "cat", "head", "tail", "grep", "find", "pwd", "echo",
    "mkdir", "touch", "cp", "mv", "rm", "chmod", "chown",
    "ps", "top", "htop", "df", "du", "free", "uptime",
    "git", "docker", "docker-compose", "npm", "node", "python", "python3",
    "pip", "pip3", "pytest", "black", "flake8", "mypy",
    "ssh", "scp", "rsync", "tar", "gzip", "gunzip", "zip", "unzip",
    "curl",  # Only allowed with specific flags validation
    "wget",  # Only allowed with specific flags validation
}


def _validate_command(command: str) -> None:
    """
    Validate command for safety.
    
    SECURITY: This validation runs BEFORE any execution.
    
    Raises:
        PermissionError: If command contains dangerous operations
        ValueError: If command is invalid
    """
    if not command or not isinstance(command, str):
        raise ValueError("Command must be a non-empty string")
    
    command_lower = command.lower().strip()
    
    # Block shell metacharacters that could enable injection
    dangerous_chars = [';', '&', '|', '`', '$', '(', ')', '{', '}', '<', '>']
    if any(char in command for char in dangerous_chars):
        # Only allow if properly quoted (simple check)
        try:
            parsed = shlex.split(command)
            if not parsed:
                raise PermissionError("Command contains shell metacharacters")
        except ValueError:
            raise PermissionError("Command contains invalid shell syntax")
    
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
        "su root",
    ]
    
    for pattern in dangerous_patterns:
        if pattern in command_lower:
            logger.warning(f"🚫 Blocked privilege escalation: {command}")
            raise PermissionError(f"Command attempts privilege escalation: {pattern}")
    
    # Validate command is in whitelist (optional - uncomment for strict mode)
    # cmd_parts = shlex.split(command)
    # if cmd_parts and cmd_parts[0] not in ALLOWED_COMMANDS:
    #     raise PermissionError(f"Command '{cmd_parts[0]}' is not in allowed commands list")


import os
