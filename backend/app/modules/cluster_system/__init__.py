"""
BRAiN Cluster System

Dynamic Multi-Agent Cluster Management with Blueprint-based creation,
auto-scaling, and lifecycle management (Myzel-Prinzip).

Key Components:
- Blueprints: YAML-based cluster definitions
- Creator: Spawn clusters from blueprints
- Manager: Lifecycle (create/scale/hibernate/destroy)
- Manifests: Generated documentation (.md files)

Usage:
    from app.modules.cluster_system.service import ClusterService

    service = ClusterService(db)
    cluster = await service.create_from_blueprint(
        blueprint_id="marketing-v1",
        name="Marketing Q1 2024"
    )
"""

__version__ = "0.1.0"
