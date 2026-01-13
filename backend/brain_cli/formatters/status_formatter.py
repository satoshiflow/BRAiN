"""
Status Output Formatter

Formats system status for terminal output using rich library.
"""

import json
from typing import Dict, Any

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text


class StatusFormatter:
    """Formats system status output"""

    def __init__(self):
        self.console = Console()

    def format_text(self, status: Dict[str, Any]) -> None:
        """Format status as rich terminal output"""
        # Header
        self.console.print()
        self.console.print(
            Panel.fit(
                f"[bold cyan]BRAiN System Status Report[/bold cyan]\n"
                f"Timestamp: {status.get('timestamp', 'N/A')}",
                border_style="cyan",
            )
        )
        self.console.print()

        # Overall Status
        overall = status.get("overall_status", "unknown")
        status_emoji = {
            "healthy": "✅",
            "degraded": "⚠️ ",
            "critical": "❌",
            "unknown": "❓",
        }.get(overall, "❓")

        status_color = {
            "healthy": "green",
            "degraded": "yellow",
            "critical": "red",
            "unknown": "white",
        }.get(overall, "white")

        self.console.print(
            f"Overall Status: {status_emoji} [{status_color}]{overall.upper()}[/{status_color}]"
        )

        uptime = status.get("uptime_seconds", 0)
        hours = int(uptime // 3600)
        minutes = int((uptime % 3600) // 60)
        seconds = int(uptime % 60)
        self.console.print(f"Uptime: {hours}h {minutes}m {seconds}s\n")

        # Immune System
        if "immune_health" in status:
            self._print_immune_system(status["immune_health"])

        # Mission System
        if "mission_health" in status:
            self._print_mission_system(status["mission_health"])

        # Agent System
        if "agent_health" in status:
            self._print_agent_system(status["agent_health"])

        # Performance Metrics
        if "audit_metrics" in status:
            self._print_performance(status["audit_metrics"])

        # Bottlenecks
        bottlenecks = status.get("bottlenecks", [])
        if bottlenecks:
            self._print_bottlenecks(bottlenecks)

        # Recommendations
        recommendations = status.get("recommendations", [])
        if recommendations:
            self._print_recommendations(recommendations)

    def _print_immune_system(self, immune: Dict[str, Any]) -> None:
        """Print immune system status"""
        self.console.print("[bold]🛡️  Immune System[/bold]", style="cyan")
        self.console.print("─" * 60)

        status_emoji = "✅" if immune.get("active_issues", 0) == 0 else "⚠️ "
        self.console.print(f"  Status: {status_emoji} HEALTHY" if immune.get("active_issues", 0) == 0 else f"  Status: {status_emoji} ISSUES DETECTED")
        self.console.print(f"  Active Issues: {immune.get('active_issues', 0)}")
        self.console.print(f"  Critical Issues: {immune.get('critical_issues', 0)}")
        self.console.print(f"  Event Rate: {immune.get('event_rate', 0):.1f} events/min\n")

    def _print_mission_system(self, mission: Dict[str, Any]) -> None:
        """Print mission system status"""
        self.console.print("[bold]📋 Mission System[/bold]", style="cyan")
        self.console.print("─" * 60)

        self.console.print(f"  Queue Depth: {mission.get('queue_depth', 0)}")
        self.console.print(f"  Running: {mission.get('running_missions', 0)}")
        self.console.print(f"  Pending: {mission.get('pending_missions', 0)}")

        completed = mission.get('completed_today', 0)
        failed = mission.get('failed_today', 0)
        total = completed + failed
        completion_rate = (completed / total * 100) if total > 0 else 0
        self.console.print(f"  Completion Rate: {completion_rate:.1f}%\n")

    def _print_agent_system(self, agent: Dict[str, Any]) -> None:
        """Print agent system status"""
        self.console.print("[bold]🤖 Agent System[/bold]", style="cyan")
        self.console.print("─" * 60)

        total = agent.get('total_agents', 0)
        active = agent.get('active_agents', 0)
        idle = agent.get('idle_agents', 0)

        self.console.print(f"  Total Agents: {total}")
        self.console.print(f"  Active: {active}")
        self.console.print(f"  Idle: {idle}")

        utilization = (active / total * 100) if total > 0 else 0
        self.console.print(f"  Utilization: {utilization:.1f}%\n")

    def _print_performance(self, metrics: Dict[str, Any]) -> None:
        """Print performance metrics"""
        self.console.print("[bold]📊 Performance Metrics[/bold]", style="cyan")
        self.console.print("─" * 60)

        self.console.print(f"  Avg Latency: {metrics.get('avg_latency_ms', 0):.1f}ms")
        self.console.print(f"  P95 Latency: {metrics.get('p95_latency_ms', 0):.1f}ms")
        self.console.print(f"  Memory Usage: {metrics.get('memory_usage_mb', 0):.1f} MB")
        self.console.print(f"  CPU Usage: {metrics.get('cpu_usage_percent', 0):.1f}%")
        self.console.print(f"  Edge-of-Chaos Score: {metrics.get('edge_of_chaos_score', 0):.2f}\n")

    def _print_bottlenecks(self, bottlenecks: list) -> None:
        """Print bottleneck information"""
        self.console.print(f"[bold yellow]⚠️  Bottlenecks Detected: {len(bottlenecks)}[/bold yellow]")

        for b in bottlenecks:
            severity = b.get("severity", "unknown")
            severity_color = {
                "low": "yellow",
                "medium": "orange",
                "high": "red",
            }.get(severity, "white")

            self.console.print(
                f"  [{severity_color}]{severity.upper()}[/{severity_color}]: {b.get('type', 'unknown')} - {b.get('description', 'N/A')}"
            )
        self.console.print()

    def _print_recommendations(self, recommendations: list) -> None:
        """Print optimization recommendations"""
        self.console.print(f"[bold green]💡 Recommendations: {len(recommendations)}[/bold green]")

        for r in recommendations:
            priority = r.get("priority", "unknown")
            priority_emoji = {
                "low": "🟢",
                "medium": "🟡",
                "high": "🔴",
            }.get(priority, "⚪")

            self.console.print(
                f"  {priority_emoji} [{r.get('category', 'general')}] {r.get('description', 'N/A')}"
            )
        self.console.print()

    def format_json(self, status: Dict[str, Any]) -> None:
        """Format status as JSON"""
        self.console.print_json(json.dumps(status, indent=2))

    def format_summary(self, status: Dict[str, Any]) -> None:
        """Format status as one-line summary"""
        overall = status.get("overall_status", "unknown")
        status_emoji = {
            "healthy": "✅",
            "degraded": "⚠️ ",
            "critical": "❌",
            "unknown": "❓",
        }.get(overall, "❓")

        missions = status.get("mission_health", {})
        agents = status.get("agent_health", {})
        uptime = status.get("uptime_seconds", 0)

        self.console.print(
            f"{status_emoji} {overall.upper()} | "
            f"Uptime: {int(uptime//3600)}h {int((uptime%3600)//60)}m | "
            f"Missions: {missions.get('queue_depth', 0)} queued, {missions.get('running_missions', 0)} running | "
            f"Agents: {agents.get('total_agents', 0)} total, {agents.get('active_agents', 0)} active"
        )
