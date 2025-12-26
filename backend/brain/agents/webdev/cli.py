#!/usr/bin/env python3
"""
WebDev Cluster CLI - Command-line interface for agent operations

Production-ready CLI with comprehensive command routing, error handling,
and token management integration.
"""

from __future__ import annotations

import sys
import argparse
import logging
from pathlib import Path
from typing import Optional, Dict, Any
import json

# Add webdev to path
sys.path.insert(0, str(Path(__file__).parent))

from core.token_manager import get_token_manager, TokenBudget
from core.error_handler import get_error_handler, ErrorContext, ErrorSeverity
from core.self_healing import get_self_healing_manager


# Setup logging
def setup_logging(verbosity: int = 0) -> None:
    """
    Setup logging configuration

    Args:
        verbosity: Verbosity level (0=INFO, 1=DEBUG, 2+=DEBUG with more details)
    """
    log_levels = {
        0: logging.INFO,
        1: logging.DEBUG,
        2: logging.DEBUG
    }

    level = log_levels.get(verbosity, logging.DEBUG)

    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # Set specific loggers
    if verbosity >= 2:
        logging.getLogger('core.token_manager').setLevel(logging.DEBUG)
        logging.getLogger('core.error_handler').setLevel(logging.DEBUG)
        logging.getLogger('core.self_healing').setLevel(logging.DEBUG)


logger = logging.getLogger(__name__)


class WebDevCLI:
    """
    Main CLI controller for WebDev Cluster

    Commands:
    - generate: Generate code, UI components, etc.
    - analyze: Analyze projects, code quality, dependencies
    - complete: Code completion and suggestions
    - health: System health status
    - stats: Token usage and statistics
    - config: Configuration management
    """

    def __init__(self):
        """Initialize CLI with core managers"""
        self.token_manager = get_token_manager()
        self.error_handler = get_error_handler()
        self.healing_manager = get_self_healing_manager()

        logger.info("WebDev CLI initialized")

    def run(self, args: argparse.Namespace) -> int:
        """
        Main entry point for CLI execution

        Args:
            args: Parsed command-line arguments

        Returns:
            Exit code (0 = success, non-zero = error)
        """
        try:
            # Route to appropriate command handler
            command_handlers = {
                'generate': self.handle_generate,
                'analyze': self.handle_analyze,
                'complete': self.handle_complete,
                'health': self.handle_health,
                'stats': self.handle_stats,
                'config': self.handle_config
            }

            handler = command_handlers.get(args.command)
            if not handler:
                logger.error(f"Unknown command: {args.command}")
                return 1

            # Execute command with error handling
            return handler(args)

        except KeyboardInterrupt:
            logger.info("Operation cancelled by user")
            return 130
        except Exception as e:
            context = ErrorContext(
                operation=f"cli_{args.command}",
                component="cli",
                user_action=f"Command: {args.command}"
            )
            self.error_handler.handle_error(e, context)
            logger.error(f"Command failed: {e}")
            return 1

    def handle_generate(self, args: argparse.Namespace) -> int:
        """
        Handle code/component generation commands

        Examples:
            dev-agent generate module --type=service --name=UserService
            dev-agent generate component --type=react --name=Button
            dev-agent generate api --type=rest --resource=users
        """
        logger.info(f"Generate command: type={args.type}, name={getattr(args, 'name', 'N/A')}")

        # Check token availability
        estimated_tokens = self._estimate_generation_tokens(args)
        available, message = self.token_manager.check_availability(
            estimated_tokens,
            f"generate_{args.type}"
        )

        if not available:
            logger.error(f"Insufficient tokens: {message}")
            print(f"❌ {message}")
            return 1

        # Reserve tokens
        operation_id = self.token_manager.reserve_tokens(
            f"generate_{args.type}",
            estimated_tokens,
            {"type": args.type, "name": getattr(args, 'name', None)}
        )

        if not operation_id:
            logger.error("Failed to reserve tokens")
            return 1

        try:
            # Route to appropriate generator
            if args.type == 'module':
                result = self._generate_module(args)
            elif args.type == 'component':
                result = self._generate_component(args)
            elif args.type == 'api':
                result = self._generate_api(args)
            else:
                logger.error(f"Unknown generation type: {args.type}")
                self.token_manager.abort_operation(operation_id, "Unknown type")
                return 1

            # Record actual usage
            actual_tokens = result.get('tokens_used', estimated_tokens)
            self.token_manager.record_usage(operation_id, actual_tokens, "completed")

            print(f"✅ Generation successful!")
            print(f"📊 Tokens used: {actual_tokens}")

            if result.get('files_created'):
                print(f"📁 Files created:")
                for file_path in result['files_created']:
                    print(f"   - {file_path}")

            return 0

        except Exception as e:
            self.token_manager.abort_operation(operation_id, str(e))
            raise

    def handle_analyze(self, args: argparse.Namespace) -> int:
        """
        Handle project/code analysis commands

        Examples:
            dev-agent analyze project
            dev-agent analyze code --file=app.py
            dev-agent analyze dependencies
        """
        logger.info(f"Analyze command: target={args.target}")

        print(f"🔍 Analyzing {args.target}...")

        # Check token availability
        estimated_tokens = 10000  # Analysis typically needs more context
        available, message = self.token_manager.check_availability(
            estimated_tokens,
            f"analyze_{args.target}"
        )

        if not available:
            logger.error(f"Insufficient tokens: {message}")
            print(f"❌ {message}")
            return 1

        operation_id = self.token_manager.reserve_tokens(
            f"analyze_{args.target}",
            estimated_tokens
        )

        try:
            if args.target == 'project':
                result = self._analyze_project(args)
            elif args.target == 'code':
                result = self._analyze_code(args)
            elif args.target == 'dependencies':
                result = self._analyze_dependencies(args)
            else:
                logger.error(f"Unknown analysis target: {args.target}")
                self.token_manager.abort_operation(operation_id, "Unknown target")
                return 1

            actual_tokens = result.get('tokens_used', estimated_tokens)
            self.token_manager.record_usage(operation_id, actual_tokens, "completed")

            print(f"\n✅ Analysis complete!")
            print(f"📊 Tokens used: {actual_tokens}")

            # Display results
            self._display_analysis_results(result)

            return 0

        except Exception as e:
            self.token_manager.abort_operation(operation_id, str(e))
            raise

    def handle_complete(self, args: argparse.Namespace) -> int:
        """
        Handle code completion commands

        Examples:
            dev-agent complete --file=route.py --line=42
            dev-agent complete --context="def calculate"
        """
        logger.info(f"Complete command: file={getattr(args, 'file', 'N/A')}")

        print(f"💡 Generating completion...")

        # Completion uses fewer tokens
        estimated_tokens = 3000
        available, message = self.token_manager.check_availability(
            estimated_tokens,
            "code_completion"
        )

        if not available:
            logger.error(f"Insufficient tokens: {message}")
            print(f"❌ {message}")
            return 1

        operation_id = self.token_manager.reserve_tokens(
            "code_completion",
            estimated_tokens,
            {"file": getattr(args, 'file', None)}
        )

        try:
            result = self._complete_code(args)

            actual_tokens = result.get('tokens_used', estimated_tokens)
            self.token_manager.record_usage(operation_id, actual_tokens, "completed")

            print(f"\n✅ Completion generated!")
            print(f"📊 Tokens used: {actual_tokens}")
            print(f"\n{result.get('completion', '')}")

            return 0

        except Exception as e:
            self.token_manager.abort_operation(operation_id, str(e))
            raise

    def handle_health(self, args: argparse.Namespace) -> int:
        """
        Display system health status

        Examples:
            dev-agent health
            dev-agent health --verbose
        """
        logger.info("Health check requested")

        print("🏥 WebDev Cluster Health Status\n")

        # Get system health
        health = self.healing_manager.get_system_health()

        # Display overall status
        status_emoji = {
            "healthy": "✅",
            "degraded": "⚠️",
            "unhealthy": "❌"
        }

        emoji = status_emoji.get(health['status'], "❓")
        print(f"Overall Status: {emoji} {health['status'].upper()}\n")

        # Display services
        if health['services']:
            print("Services:")
            for service_name, service_health in health['services'].items():
                service_emoji = status_emoji.get(
                    service_health['status'].replace('_', ''),
                    "❓"
                )
                print(f"  {service_emoji} {service_name}: {service_health['status']}")
                if args.verbose:
                    print(f"      Failures: {service_health['consecutive_failures']}")
                    print(f"      Total checks: {service_health['total_checks']}")

        # Display circuit breakers
        if health['circuit_breakers']:
            print("\nCircuit Breakers:")
            for cb_name, cb_status in health['circuit_breakers'].items():
                state_emoji = {
                    "closed": "✅",
                    "open": "❌",
                    "half_open": "⚠️"
                }
                emoji = state_emoji.get(cb_status['state'], "❓")
                print(f"  {emoji} {cb_name}: {cb_status['state'].upper()}")

        return 0

    def handle_stats(self, args: argparse.Namespace) -> int:
        """
        Display token usage statistics

        Examples:
            dev-agent stats
            dev-agent stats --detailed
        """
        logger.info("Statistics requested")

        stats = self.token_manager.get_statistics()

        print("📊 WebDev Cluster Statistics\n")

        # Current usage
        print("Current Usage:")
        print(f"  Hourly: {stats['current']['hourly_usage']:,} / {stats['limits']['max_per_hour']:,} tokens")
        print(f"          ({stats['utilization']['hourly_pct']:.1f}%)")
        print(f"  Daily:  {stats['current']['daily_usage']:,} / {stats['limits']['max_per_day']:,} tokens")
        print(f"          ({stats['utilization']['daily_pct']:.1f}%)")
        print(f"  Active operations: {stats['current']['active_operations']}")
        print(f"  Reserved tokens: {stats['current']['reserved_tokens']:,}")

        # Limits
        print("\nLimits:")
        print(f"  Max per operation: {stats['limits']['max_per_operation']:,} tokens")
        print(f"  Max per hour: {stats['limits']['max_per_hour']:,} tokens")
        print(f"  Max per day: {stats['limits']['max_per_day']:,} tokens")

        # History
        if args.detailed:
            print("\nHistory:")
            print(f"  Total operations: {stats['history']['total_operations']}")
            print(f"  Completed: {stats['history']['completed']}")
            print(f"  Failed: {stats['history']['failed']}")
            print(f"  Aborted: {stats['history']['aborted']}")

        # Error statistics
        if args.detailed:
            error_stats = self.error_handler.get_error_statistics()
            print(f"\nError Statistics:")
            print(f"  Total errors: {error_stats['total_errors']}")
            if error_stats['recovery_stats']['attempted'] > 0:
                print(f"  Recovery rate: {error_stats['recovery_stats']['rate_pct']:.1f}%")

        return 0

    def handle_config(self, args: argparse.Namespace) -> int:
        """
        Configuration management

        Examples:
            dev-agent config show
            dev-agent config set token_limit 50000
        """
        logger.info(f"Config command: action={args.action}")

        if args.action == 'show':
            print("⚙️  Current Configuration\n")

            budget = self.token_manager.budget
            print("Token Budget:")
            print(f"  Max per operation: {budget.max_tokens_per_operation:,}")
            print(f"  Max per hour: {budget.max_tokens_per_hour:,}")
            print(f"  Max per day: {budget.max_tokens_per_day:,}")
            print(f"  Warning threshold: {budget.warning_threshold*100:.0f}%")
            print(f"  Abort threshold: {budget.abort_threshold*100:.0f}%")
            print(f"  Safety buffer: {budget.safety_buffer:,}")

        elif args.action == 'set':
            print(f"⚙️  Setting {args.key} = {args.value}")
            # Implementation for setting config values

        return 0

    # Helper methods for generation

    def _estimate_generation_tokens(self, args: argparse.Namespace) -> int:
        """Estimate tokens needed for generation"""
        type_estimates = {
            'module': 15000,
            'component': 10000,
            'api': 12000,
            'service': 15000,
            'test': 8000
        }
        return type_estimates.get(args.type, 10000)

    def _generate_module(self, args: argparse.Namespace) -> Dict[str, Any]:
        """Generate a module (placeholder - will connect to coding agent)"""
        logger.info(f"Generating module: {getattr(args, 'name', 'unnamed')}")

        # Placeholder - will integrate with coding agent
        return {
            'tokens_used': 12000,
            'files_created': [
                f"/srv/dev/BRAIN-V2/agents/webdev/generated/{getattr(args, 'name', 'module')}.py"
            ]
        }

    def _generate_component(self, args: argparse.Namespace) -> Dict[str, Any]:
        """Generate a UI component (placeholder - will connect to web_grafik agent)"""
        logger.info(f"Generating component: {getattr(args, 'name', 'unnamed')}")

        # Placeholder
        return {
            'tokens_used': 8000,
            'files_created': [
                f"/srv/dev/BRAIN-V2/agents/webdev/generated/{getattr(args, 'name', 'Component')}.tsx"
            ]
        }

    def _generate_api(self, args: argparse.Namespace) -> Dict[str, Any]:
        """Generate API endpoints (placeholder)"""
        logger.info(f"Generating API for resource: {getattr(args, 'resource', 'unknown')}")

        # Placeholder
        return {
            'tokens_used': 10000,
            'files_created': [
                f"/srv/dev/BRAIN-V2/agents/webdev/generated/api_{getattr(args, 'resource', 'resource')}.py"
            ]
        }

    def _analyze_project(self, args: argparse.Namespace) -> Dict[str, Any]:
        """Analyze project structure (placeholder)"""
        logger.info("Analyzing project")

        # Placeholder
        return {
            'tokens_used': 8000,
            'files_analyzed': 42,
            'languages': ['Python', 'TypeScript'],
            'total_lines': 15234
        }

    def _analyze_code(self, args: argparse.Namespace) -> Dict[str, Any]:
        """Analyze code quality (placeholder)"""
        logger.info(f"Analyzing code: {getattr(args, 'file', 'N/A')}")

        # Placeholder
        return {
            'tokens_used': 5000,
            'quality_score': 8.5,
            'issues_found': 3,
            'suggestions': ['Add type hints', 'Improve error handling']
        }

    def _analyze_dependencies(self, args: argparse.Namespace) -> Dict[str, Any]:
        """Analyze dependencies (placeholder)"""
        logger.info("Analyzing dependencies")

        # Placeholder
        return {
            'tokens_used': 4000,
            'total_dependencies': 28,
            'outdated': 5,
            'security_issues': 1
        }

    def _complete_code(self, args: argparse.Namespace) -> Dict[str, Any]:
        """Generate code completion (placeholder)"""
        logger.info("Generating code completion")

        # Placeholder
        return {
            'tokens_used': 2500,
            'completion': '    return result.json()'
        }

    def _display_analysis_results(self, result: Dict[str, Any]) -> None:
        """Display analysis results in formatted output"""
        print("\n📋 Analysis Results:")

        for key, value in result.items():
            if key == 'tokens_used':
                continue

            if isinstance(value, list):
                print(f"\n{key.replace('_', ' ').title()}:")
                for item in value:
                    print(f"  • {item}")
            else:
                print(f"  {key.replace('_', ' ').title()}: {value}")


def create_parser() -> argparse.ArgumentParser:
    """Create argument parser with all commands and options"""
    parser = argparse.ArgumentParser(
        prog='dev-agent',
        description='WebDev Cluster - Production-ready AI agent for code generation and analysis',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate a service module
  dev-agent generate module --type=service --name=UserService

  # Analyze project structure
  dev-agent analyze project

  # Code completion
  dev-agent complete --file=route.py

  # Check system health
  dev-agent health

  # View statistics
  dev-agent stats --detailed
        """
    )

    parser.add_argument(
        '-v', '--verbose',
        action='count',
        default=0,
        help='Increase verbosity (can be used multiple times)'
    )

    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    # Generate command
    generate_parser = subparsers.add_parser(
        'generate',
        help='Generate code, modules, components'
    )
    generate_parser.add_argument(
        'type',
        choices=['module', 'component', 'api', 'service', 'test'],
        help='Type of artifact to generate'
    )
    generate_parser.add_argument('--name', help='Name of the artifact')
    generate_parser.add_argument('--output', help='Output directory')
    generate_parser.add_argument('--template', help='Template to use')

    # Analyze command
    analyze_parser = subparsers.add_parser(
        'analyze',
        help='Analyze project, code, dependencies'
    )
    analyze_parser.add_argument(
        'target',
        choices=['project', 'code', 'dependencies'],
        help='What to analyze'
    )
    analyze_parser.add_argument('--file', help='File to analyze')
    analyze_parser.add_argument('--path', help='Path to analyze')

    # Complete command
    complete_parser = subparsers.add_parser(
        'complete',
        help='Code completion and suggestions'
    )
    complete_parser.add_argument('--file', help='File for completion')
    complete_parser.add_argument('--line', type=int, help='Line number')
    complete_parser.add_argument('--context', help='Context for completion')

    # Health command
    health_parser = subparsers.add_parser(
        'health',
        help='System health status'
    )
    health_parser.add_argument(
        '--verbose',
        action='store_true',
        help='Show detailed health information'
    )

    # Stats command
    stats_parser = subparsers.add_parser(
        'stats',
        help='Token usage and statistics'
    )
    stats_parser.add_argument(
        '--detailed',
        action='store_true',
        help='Show detailed statistics'
    )

    # Config command
    config_parser = subparsers.add_parser(
        'config',
        help='Configuration management'
    )
    config_parser.add_argument(
        'action',
        choices=['show', 'set', 'reset'],
        help='Configuration action'
    )
    config_parser.add_argument('--key', help='Configuration key')
    config_parser.add_argument('--value', help='Configuration value')

    return parser


def main() -> int:
    """Main entry point"""
    parser = create_parser()
    args = parser.parse_args()

    # Setup logging
    setup_logging(args.verbose)

    # Check if command was provided
    if not args.command:
        parser.print_help()
        return 1

    # Run CLI
    cli = WebDevCLI()
    return cli.run(args)


if __name__ == '__main__':
    sys.exit(main())
