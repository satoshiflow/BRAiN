"""IntegrationCore module - External service integrations"""

from .claude_bridge import ClaudeBridge, ClaudeRequest, ClaudeResponse
from .github_connector import GitHubConnector, GitHubRepo, PullRequest, Issue, PRState, IssueState
from .language_parser import LanguageParser, parse_code, ParsedCode, Symbol, SymbolType, Language

__all__ = [
    'ClaudeBridge',
    'ClaudeRequest',
    'ClaudeResponse',
    'GitHubConnector',
    'GitHubRepo',
    'PullRequest',
    'Issue',
    'PRState',
    'IssueState',
    'LanguageParser',
    'parse_code',
    'ParsedCode',
    'Symbol',
    'SymbolType',
    'Language',
]
