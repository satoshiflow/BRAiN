"""
BRAiN Workers

Horizontal scalable worker pool for async task processing.

Workers:
- ClusterWorker: Processes cluster operations (spawn, scale, etc.)
- MissionWorker: Processes mission tasks (existing)

Each worker can run as N replicas in Coolify for horizontal scaling.
"""

__version__ = "0.1.0"
