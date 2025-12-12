"""
Language Parser - Multi-language code parsing and analysis

Provides AST parsing, symbol extraction, and code structure analysis
for multiple programming languages.
"""

from __future__ import annotations

import sys
import ast
import re
from pathlib import Path
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, field
from enum import Enum
import logging

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.token_manager import get_token_manager
from core.error_handler import with_error_handling

logger = logging.getLogger(__name__)


class Language(str, Enum):
    """Supported languages"""
    PYTHON = "python"
    TYPESCRIPT = "typescript"
    JAVASCRIPT = "javascript"
    JAVA = "java"
    GO = "go"
    RUST = "rust"


class SymbolType(str, Enum):
    """Symbol types"""
    CLASS = "class"
    FUNCTION = "function"
    METHOD = "method"
    VARIABLE = "variable"
    CONSTANT = "constant"
    INTERFACE = "interface"
    TYPE = "type"


@dataclass
class Symbol:
    """Code symbol"""
    name: str
    type: SymbolType
    line_number: int
    column: Optional[int] = None
    docstring: Optional[str] = None
    parameters: List[str] = field(default_factory=list)
    return_type: Optional[str] = None
    decorators: List[str] = field(default_factory=list)
    modifiers: List[str] = field(default_factory=list)


@dataclass
class ParsedCode:
    """Parsed code structure"""
    language: Language
    symbols: List[Symbol]
    imports: List[str]
    exports: List[str]
    dependencies: Set[str]
    complexity: int
    metadata: Dict[str, Any] = field(default_factory=dict)


class LanguageParser:
    """
    Multi-language code parser

    Features:
    - AST parsing
    - Symbol extraction
    - Dependency analysis
    - Complexity calculation
    - Import/export tracking
    """

    def __init__(self):
        """Initialize language parser"""
        self.token_manager = get_token_manager()
        logger.info("LanguageParser initialized")

    @with_error_handling("parse_code", "language_parser", reraise=True)
    def parse(
        self,
        code: str,
        language: Language,
        file_path: Optional[Path] = None
    ) -> ParsedCode:
        """
        Parse code and extract structure

        Args:
            code: Source code
            language: Programming language
            file_path: Optional file path

        Returns:
            Parsed code structure
        """
        logger.info(f"Parsing {language.value} code")

        # Estimate tokens
        estimated_tokens = len(code.split()) * 0.5
        available, msg = self.token_manager.check_availability(
            int(estimated_tokens),
            "code_parsing"
        )

        if not available:
            raise Exception(f"Insufficient tokens: {msg}")

        operation_id = self.token_manager.reserve_tokens(
            "code_parsing",
            int(estimated_tokens)
        )

        try:
            if language == Language.PYTHON:
                result = self._parse_python(code)
            elif language in [Language.TYPESCRIPT, Language.JAVASCRIPT]:
                result = self._parse_javascript(code, language)
            else:
                result = self._parse_generic(code, language)

            actual_tokens = int(len(code.split()) * 0.4)
            self.token_manager.record_usage(operation_id, actual_tokens, "completed")

            return result

        except Exception as e:
            self.token_manager.abort_operation(operation_id, str(e))
            raise

    def _parse_python(self, code: str) -> ParsedCode:
        """Parse Python code"""
        symbols = []
        imports = []
        exports = []
        dependencies = set()

        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            logger.error(f"Python syntax error: {e}")
            return ParsedCode(
                language=Language.PYTHON,
                symbols=[],
                imports=[],
                exports=[],
                dependencies=set(),
                complexity=0
            )

        # Extract imports
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(alias.name)
                    dependencies.add(alias.name.split('.')[0])
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imports.append(node.module)
                    dependencies.add(node.module.split('.')[0])

        # Extract symbols
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                symbols.append(Symbol(
                    name=node.name,
                    type=SymbolType.CLASS,
                    line_number=node.lineno,
                    column=node.col_offset,
                    docstring=ast.get_docstring(node),
                    decorators=[d.id for d in node.decorator_list if isinstance(d, ast.Name)]
                ))
            elif isinstance(node, ast.FunctionDef):
                parameters = [arg.arg for arg in node.args.args]
                return_annotation = None
                if node.returns:
                    if isinstance(node.returns, ast.Name):
                        return_annotation = node.returns.id

                symbols.append(Symbol(
                    name=node.name,
                    type=SymbolType.FUNCTION,
                    line_number=node.lineno,
                    column=node.col_offset,
                    docstring=ast.get_docstring(node),
                    parameters=parameters,
                    return_type=return_annotation,
                    decorators=[d.id for d in node.decorator_list if isinstance(d, ast.Name)]
                ))

        # Calculate complexity
        complexity = self._calculate_complexity(tree)

        return ParsedCode(
            language=Language.PYTHON,
            symbols=symbols,
            imports=imports,
            exports=exports,  # Python doesn't have explicit exports
            dependencies=dependencies,
            complexity=complexity
        )

    def _parse_javascript(self, code: str, language: Language) -> ParsedCode:
        """Parse JavaScript/TypeScript code"""
        symbols = []
        imports = []
        exports = []
        dependencies = set()

        # Extract imports (simple regex-based)
        import_pattern = r'import\s+(?:{([^}]+)}|(\w+))\s+from\s+["\']([^"\']+)["\']'
        for match in re.finditer(import_pattern, code):
            module = match.group(3)
            imports.append(module)
            if not module.startswith('.'):
                dependencies.add(module.split('/')[0])

        # Extract exports
        export_pattern = r'export\s+(?:default\s+)?(?:class|function|const|let|var)\s+(\w+)'
        for match in re.finditer(export_pattern, code):
            exports.append(match.group(1))

        # Extract functions (simplified)
        function_pattern = r'(?:export\s+)?(?:async\s+)?function\s+(\w+)\s*\('
        for match in re.finditer(function_pattern, code):
            line_num = code[:match.start()].count('\n') + 1
            symbols.append(Symbol(
                name=match.group(1),
                type=SymbolType.FUNCTION,
                line_number=line_num
            ))

        # Extract classes (simplified)
        class_pattern = r'(?:export\s+)?class\s+(\w+)'
        for match in re.finditer(class_pattern, code):
            line_num = code[:match.start()].count('\n') + 1
            symbols.append(Symbol(
                name=match.group(1),
                type=SymbolType.CLASS,
                line_number=line_num
            ))

        return ParsedCode(
            language=language,
            symbols=symbols,
            imports=imports,
            exports=exports,
            dependencies=dependencies,
            complexity=0  # Simplified
        )

    def _parse_generic(self, code: str, language: Language) -> ParsedCode:
        """Generic parsing for unsupported languages"""
        return ParsedCode(
            language=language,
            symbols=[],
            imports=[],
            exports=[],
            dependencies=set(),
            complexity=0
        )

    def _calculate_complexity(self, tree: ast.AST) -> int:
        """Calculate cyclomatic complexity"""
        complexity = 1

        for node in ast.walk(tree):
            if isinstance(node, (ast.If, ast.While, ast.For, ast.ExceptHandler)):
                complexity += 1
            elif isinstance(node, ast.BoolOp):
                complexity += len(node.values) - 1

        return complexity

    def extract_dependencies(
        self,
        code: str,
        language: Language
    ) -> Set[str]:
        """
        Extract dependencies from code

        Args:
            code: Source code
            language: Programming language

        Returns:
            Set of dependencies
        """
        parsed = self.parse(code, language)
        return parsed.dependencies

    def find_symbol(
        self,
        code: str,
        language: Language,
        symbol_name: str
    ) -> Optional[Symbol]:
        """
        Find a specific symbol in code

        Args:
            code: Source code
            language: Programming language
            symbol_name: Symbol name to find

        Returns:
            Symbol if found, None otherwise
        """
        parsed = self.parse(code, language)

        for symbol in parsed.symbols:
            if symbol.name == symbol_name:
                return symbol

        return None


def parse_code(code: str, language: Language) -> ParsedCode:
    """Convenience function to parse code"""
    parser = LanguageParser()
    return parser.parse(code, language)
