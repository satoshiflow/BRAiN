"""Coding agent module - Code generation, completion, and review"""

from .code_generator import CodeGenerator, generate_code, CodeSpec, GeneratedCode, Language, CodeType
from .code_completer import CodeCompleter, CompletionContext, Completion
from .code_reviewer import CodeReviewer, review_code, CodeReview, CodeIssue, ReviewMetrics

__all__ = [
    'CodeGenerator',
    'generate_code',
    'CodeSpec',
    'GeneratedCode',
    'Language',
    'CodeType',
    'CodeCompleter',
    'CompletionContext',
    'Completion',
    'CodeReviewer',
    'review_code',
    'CodeReview',
    'CodeIssue',
    'ReviewMetrics',
]
