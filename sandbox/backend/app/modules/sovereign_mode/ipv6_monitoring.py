"""
IPv6 Traffic Monitoring

Monitor IPv6 traffic statistics from kernel.
"""

import subprocess
from typing import Dict, Optional
from loguru import logger
from pydantic import BaseModel
from datetime import datetime


class IPv6TrafficStats(BaseModel):
    """IPv6 traffic statistics."""

    ipv6_enabled: bool
    total_packets_received: int = 0
    total_packets_sent: int = 0
    total_bytes_received: int = 0
    total_bytes_sent: int = 0
    dropped_packets: int = 0
    blocked_packets: int = 0  # Packets blocked by firewall
    timestamp: datetime


class IPv6FirewallStats(BaseModel):
    """IPv6 firewall statistics."""

    active_rules: int
    allowed_packets: int = 0
    dropped_packets: int = 0
    rejected_packets: int = 0
    timestamp: datetime


class IPv6TrafficMonitor:
    """
    Monitor IPv6 traffic and firewall statistics.

    Reads from:
    - /proc/net/snmp6: IPv6 kernel statistics
    - ip6tables: Firewall rule statistics
    """

    def __init__(self):
        self._last_stats: Optional[IPv6TrafficStats] = None

    async def get_traffic_stats(self) -> IPv6TrafficStats:
        """
        Get IPv6 traffic statistics from kernel.

        Reads from /proc/net/snmp6 if available.
        """
        ipv6_enabled = self._check_ipv6_enabled()

        if not ipv6_enabled:
            return IPv6TrafficStats(
                ipv6_enabled=False,
                timestamp=datetime.utcnow(),
            )

        stats = self._read_snmp6_stats()

        traffic_stats = IPv6TrafficStats(
            ipv6_enabled=True,
            total_packets_received=stats.get("Ip6InReceives", 0),
            total_packets_sent=stats.get("Ip6OutRequests", 0),
            total_bytes_received=stats.get("Ip6InOctets", 0),
            total_bytes_sent=stats.get("Ip6OutOctets", 0),
            dropped_packets=stats.get("Ip6InDiscards", 0)
            + stats.get("Ip6OutDiscards", 0),
            timestamp=datetime.utcnow(),
        )

        self._last_stats = traffic_stats
        return traffic_stats

    def _check_ipv6_enabled(self) -> bool:
        """Check if IPv6 is enabled on the system."""
        try:
            result = subprocess.run(
                ["ip", "-6", "addr", "show"],
                capture_output=True,
                text=True,
                timeout=5,
            )

            if result.returncode == 0:
                # Check if there are any inet6 addresses with scope global
                for line in result.stdout.splitlines():
                    if "inet6" in line and "scope global" in line:
                        return True

            return False

        except Exception as e:
            logger.warning(f"Failed to check IPv6 status: {e}")
            return False

    def _read_snmp6_stats(self) -> Dict[str, int]:
        """
        Read IPv6 statistics from /proc/net/snmp6.

        Example content:
        ```
        Ip6InReceives                   	12345
        Ip6InHdrErrors                  	0
        Ip6InTooBigErrors               	0
        Ip6InNoRoutes                   	0
        Ip6InAddrErrors                 	0
        Ip6InUnknownProtos              	0
        Ip6InTruncatedPkts              	0
        Ip6InDiscards                   	0
        Ip6InDelivers                   	12345
        Ip6OutRequests                  	67890
        Ip6OutDiscards                  	0
        Ip6OutNoRoutes                  	0
        Ip6ReasmTimeout                 	0
        Ip6ReasmReqds                   	0
        Ip6ReasmOKs                     	0
        Ip6ReasmFails                   	0
        Ip6FragOKs                      	0
        Ip6FragFails                    	0
        Ip6FragCreates                  	0
        Ip6InMcastPkts                  	0
        Ip6OutMcastPkts                 	0
        Ip6InOctets                     	123456789
        Ip6OutOctets                    	987654321
        ```
        """
        stats = {}

        try:
            with open("/proc/net/snmp6", "r") as f:
                for line in f:
                    parts = line.strip().split()
                    if len(parts) == 2:
                        key, value = parts
                        try:
                            stats[key] = int(value)
                        except ValueError:
                            pass

        except FileNotFoundError:
            logger.debug("/proc/net/snmp6 not found (IPv6 may be disabled)")

        except Exception as e:
            logger.warning(f"Failed to read IPv6 stats: {e}")

        return stats

    async def get_firewall_stats(self) -> IPv6FirewallStats:
        """
        Get IPv6 firewall statistics.

        Reads from ip6tables -L -v -n -x.
        """
        try:
            result = subprocess.run(
                ["ip6tables", "-L", "DOCKER-USER", "-v", "-n", "-x"],
                capture_output=True,
                text=True,
                timeout=5,
            )

            if result.returncode != 0:
                return IPv6FirewallStats(
                    active_rules=0,
                    timestamp=datetime.utcnow(),
                )

            # Parse firewall statistics
            allowed = 0
            dropped = 0
            rejected = 0
            active_rules = 0

            for line in result.stdout.splitlines():
                # Skip header lines
                if line.startswith("Chain") or line.startswith("pkts"):
                    continue

                # Count rules with brain-sovereign-ipv6 comment
                if "brain-sovereign-ipv6" in line:
                    active_rules += 1

                    # Parse packet counts
                    parts = line.split()
                    if parts and parts[0].isdigit():
                        packets = int(parts[0])

                        if "ACCEPT" in line:
                            allowed += packets
                        elif "DROP" in line or "drop" in line:
                            dropped += packets
                        elif "REJECT" in line:
                            rejected += packets

            return IPv6FirewallStats(
                active_rules=active_rules,
                allowed_packets=allowed,
                dropped_packets=dropped,
                rejected_packets=rejected,
                timestamp=datetime.utcnow(),
            )

        except FileNotFoundError:
            logger.debug("ip6tables not found")
            return IPv6FirewallStats(
                active_rules=0,
                timestamp=datetime.utcnow(),
            )

        except Exception as e:
            logger.warning(f"Failed to get IPv6 firewall stats: {e}")
            return IPv6FirewallStats(
                active_rules=0,
                timestamp=datetime.utcnow(),
            )

    async def get_prometheus_metrics(self) -> str:
        """
        Export IPv6 metrics in Prometheus format.

        Example output:
        ```
        # HELP ipv6_enabled IPv6 enabled on system (1=yes, 0=no)
        # TYPE ipv6_enabled gauge
        ipv6_enabled 1.0

        # HELP ipv6_packets_received_total Total IPv6 packets received
        # TYPE ipv6_packets_received_total counter
        ipv6_packets_received_total 12345

        # HELP ipv6_firewall_active_rules Number of active IPv6 firewall rules
        # TYPE ipv6_firewall_active_rules gauge
        ipv6_firewall_active_rules 4
        ```
        """
        traffic_stats = await self.get_traffic_stats()
        firewall_stats = await self.get_firewall_stats()

        lines = []

        # IPv6 enabled
        lines.append("# HELP ipv6_enabled IPv6 enabled on system (1=yes, 0=no)")
        lines.append("# TYPE ipv6_enabled gauge")
        lines.append(f"ipv6_enabled {1.0 if traffic_stats.ipv6_enabled else 0.0}")
        lines.append("")

        # Traffic stats
        lines.append("# HELP ipv6_packets_received_total Total IPv6 packets received")
        lines.append("# TYPE ipv6_packets_received_total counter")
        lines.append(f"ipv6_packets_received_total {traffic_stats.total_packets_received}")
        lines.append("")

        lines.append("# HELP ipv6_packets_sent_total Total IPv6 packets sent")
        lines.append("# TYPE ipv6_packets_sent_total counter")
        lines.append(f"ipv6_packets_sent_total {traffic_stats.total_packets_sent}")
        lines.append("")

        lines.append("# HELP ipv6_bytes_received_total Total IPv6 bytes received")
        lines.append("# TYPE ipv6_bytes_received_total counter")
        lines.append(f"ipv6_bytes_received_total {traffic_stats.total_bytes_received}")
        lines.append("")

        lines.append("# HELP ipv6_bytes_sent_total Total IPv6 bytes sent")
        lines.append("# TYPE ipv6_bytes_sent_total counter")
        lines.append(f"ipv6_bytes_sent_total {traffic_stats.total_bytes_sent}")
        lines.append("")

        lines.append("# HELP ipv6_dropped_packets_total Total IPv6 packets dropped")
        lines.append("# TYPE ipv6_dropped_packets_total counter")
        lines.append(f"ipv6_dropped_packets_total {traffic_stats.dropped_packets}")
        lines.append("")

        # Firewall stats
        lines.append("# HELP ipv6_firewall_active_rules Number of active IPv6 firewall rules")
        lines.append("# TYPE ipv6_firewall_active_rules gauge")
        lines.append(f"ipv6_firewall_active_rules {firewall_stats.active_rules}")
        lines.append("")

        lines.append("# HELP ipv6_firewall_allowed_packets_total Packets allowed by IPv6 firewall")
        lines.append("# TYPE ipv6_firewall_allowed_packets_total counter")
        lines.append(f"ipv6_firewall_allowed_packets_total {firewall_stats.allowed_packets}")
        lines.append("")

        lines.append("# HELP ipv6_firewall_dropped_packets_total Packets dropped by IPv6 firewall")
        lines.append("# TYPE ipv6_firewall_dropped_packets_total counter")
        lines.append(f"ipv6_firewall_dropped_packets_total {firewall_stats.dropped_packets}")

        return "\n".join(lines)


# Singleton
_monitor: Optional[IPv6TrafficMonitor] = None


def get_ipv6_traffic_monitor() -> IPv6TrafficMonitor:
    """Get singleton IPv6 traffic monitor."""
    global _monitor
    if _monitor is None:
        _monitor = IPv6TrafficMonitor()
    return _monitor
