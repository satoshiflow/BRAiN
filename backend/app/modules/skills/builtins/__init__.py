"""
Built-in Skills Package

Default skills that ship with BRAiN:
- http_request: Make HTTP requests
- file_read: Read files from filesystem
- file_write: Write files to filesystem
- shell_command: Execute shell commands
- web_search: Search the web (placeholder)
"""

from . import http_request
from . import file_read
from . import file_write
from . import shell_command
from . import web_search

__all__ = [
    "http_request",
    "file_read",
    "file_write",
    "shell_command",
    "web_search",
]

# Export manifests for easy access
BUILTIN_SKILLS = {
    "http_request": http_request.MANIFEST,
    "file_read": file_read.MANIFEST,
    "file_write": file_write.MANIFEST,
    "shell_command": shell_command.MANIFEST,
    "web_search": web_search.MANIFEST,
}
