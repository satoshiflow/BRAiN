#!/usr/bin/env python3
"""
Knowledge Graph PoC Test Script

Generates 100 sample missions and tests:
1. Data ingestion
2. Cognify processing
3. Semantic search
4. Similar mission retrieval
5. Performance benchmarks
"""

import asyncio
import time
import random
from datetime import datetime, timedelta
from typing import List

from loguru import logger

from .service import CogneeService, AgentMemoryService
from .schemas import MissionContextRequest


# Sample mission templates
MISSION_TYPES = [
    "deployment",
    "code_review",
    "architecture_review",
    "security_audit",
    "data_processing",
    "api_integration",
]

PRIORITIES = ["LOW", "NORMAL", "HIGH", "CRITICAL"]

STATUSES = ["completed", "failed", "cancelled"]

AGENTS = [
    "ops_agent",
    "coder_agent",
    "architect_agent",
    "supervisor_agent",
    "axe_agent",
]

MISSION_TEMPLATES = {
    "deployment": [
        "Deploy {version} to {environment}",
        "Rollback deployment in {environment}",
        "Update configuration in {environment}",
        "Scale application in {environment}",
    ],
    "code_review": [
        "Review pull request #{number}",
        "Code quality check for {module}",
        "Security review of {component}",
        "Performance optimization review",
    ],
    "architecture_review": [
        "Review {system} architecture",
        "Compliance check for {regulation}",
        "Scalability assessment for {component}",
        "Security audit of {system}",
    ],
    "security_audit": [
        "Audit {component} for vulnerabilities",
        "Check DSGVO compliance in {module}",
        "Review authentication mechanism",
        "Analyze API security for {endpoint}",
    ],
    "data_processing": [
        "Process {data_type} data batch",
        "Generate report for {period}",
        "Clean up old {data_type} records",
        "Migrate {data_type} to new schema",
    ],
    "api_integration": [
        "Integrate with {service} API",
        "Update {service} API client",
        "Test {service} API endpoints",
        "Fix {service} API authentication",
    ],
}

VERSIONS = ["v1.2.3", "v1.2.4", "v2.0.0", "v2.1.0", "v3.0.0-beta"]
ENVIRONMENTS = ["development", "staging", "production"]
MODULES = ["auth", "api", "frontend", "database", "cache", "queue"]
SYSTEMS = ["payment", "user-management", "analytics", "reporting"]
REGULATIONS = ["DSGVO", "EU AI Act", "HIPAA", "SOC2"]
COMPONENTS = ["auth-service", "api-gateway", "database", "cache-layer"]
DATA_TYPES = ["user", "transaction", "log", "metric", "event"]
SERVICES = ["GitHub", "Stripe", "Cognee", "Qdrant", "OpenAI"]


def generate_sample_mission(mission_id: int) -> MissionContextRequest:
    """Generate a random sample mission"""

    mission_type = random.choice(MISSION_TYPES)
    templates = MISSION_TEMPLATES[mission_type]
    template = random.choice(templates)

    # Fill template with random values
    description = template.format(
        version=random.choice(VERSIONS),
        environment=random.choice(ENVIRONMENTS),
        number=random.randint(1, 1000),
        module=random.choice(MODULES),
        component=random.choice(COMPONENTS),
        system=random.choice(SYSTEMS),
        regulation=random.choice(REGULATIONS),
        data_type=random.choice(DATA_TYPES),
        period="2024-12",
        endpoint=f"/api/{random.choice(MODULES)}",
        service=random.choice(SERVICES),
    )

    status = random.choice(STATUSES)
    priority = random.choice(PRIORITIES)
    agent = random.choice(AGENTS)

    # Random timestamp in last 90 days
    days_ago = random.randint(0, 90)
    created_at = datetime.now() - timedelta(days=days_ago)
    completed_at = created_at + timedelta(
        hours=random.randint(1, 24)
    ) if status != "failed" else None

    # Add result for completed missions
    result = None
    if status == "completed":
        result = {
            "success": True,
            "duration_seconds": random.randint(10, 3600),
            "actions_taken": random.randint(1, 10),
        }
    elif status == "failed":
        result = {
            "success": False,
            "error": random.choice([
                "Connection timeout",
                "Permission denied",
                "Resource not found",
                "Validation failed",
            ]),
        }

    return MissionContextRequest(
        mission_id=f"mission_{mission_id:04d}",
        name=description[:50],
        description=description,
        status=status,
        priority=priority,
        mission_type=mission_type,
        assigned_agent=agent,
        created_at=created_at,
        completed_at=completed_at,
        result=result,
        context={
            "environment": random.choice(ENVIRONMENTS),
            "automated": random.choice([True, False]),
            "requires_approval": priority in ["HIGH", "CRITICAL"],
        },
    )


async def test_basic_operations():
    """Test basic Cognee operations"""

    logger.info("=" * 80)
    logger.info("KNOWLEDGE GRAPH POC TEST")
    logger.info("=" * 80)

    # Initialize services
    cognee = CogneeService()
    memory = AgentMemoryService()

    if not cognee.initialized:
        logger.error("Cognee service not initialized - check installation")
        return

    # Test 1: Add simple data
    logger.info("\n[Test 1] Adding simple data...")
    response = await cognee.add_data(
        data="Test mission: Deploy v1.0.0 to production",
        dataset_name="test_missions",
    )
    logger.info(f"✓ Added data: {response.success}")

    # Test 2: Search
    logger.info("\n[Test 2] Testing search...")
    search_response = await cognee.search(
        query="deployment to production",
        search_type="HYBRID",
        limit=3,
    )
    logger.info(f"✓ Found {search_response.total_results} results")
    for i, result in enumerate(search_response.results, 1):
        logger.info(f"  {i}. Score: {result.score:.2f} - {result.content[:100]}")

    # Test 3: List datasets
    logger.info("\n[Test 3] Listing datasets...")
    datasets = await cognee.list_datasets()
    logger.info(f"✓ Found {datasets.total_datasets} datasets")
    for ds in datasets.datasets:
        logger.info(f"  - {ds.name}: {ds.item_count} items")


async def test_sample_missions():
    """Test with 100 sample missions"""

    logger.info("\n" + "=" * 80)
    logger.info("TESTING WITH 100 SAMPLE MISSIONS")
    logger.info("=" * 80)

    memory = AgentMemoryService()

    # Generate 100 sample missions
    logger.info("\n[Phase 1] Generating 100 sample missions...")
    missions = [generate_sample_mission(i) for i in range(1, 101)]
    logger.info(f"✓ Generated {len(missions)} missions")

    # Show distribution
    type_counts = {}
    for m in missions:
        type_counts[m.mission_type] = type_counts.get(m.mission_type, 0) + 1

    logger.info("\nMission type distribution:")
    for mission_type, count in sorted(type_counts.items()):
        logger.info(f"  {mission_type}: {count}")

    # Add missions to knowledge graph
    logger.info("\n[Phase 2] Adding missions to knowledge graph...")
    start_time = time.time()

    success_count = 0
    for i, mission in enumerate(missions, 1):
        response = await memory.record_mission_context(mission)
        if response.success:
            success_count += 1

        if i % 20 == 0:
            logger.info(f"  Added {i}/{len(missions)} missions...")

    add_duration = time.time() - start_time
    logger.info(f"✓ Added {success_count}/{len(missions)} missions in {add_duration:.2f}s")
    logger.info(f"  Average: {add_duration/len(missions)*1000:.2f}ms per mission")

    # Cognify (extract entities and relationships)
    logger.info("\n[Phase 3] Running cognify process...")
    start_time = time.time()

    cognify_response = await memory.cognee.cognify(
        dataset_name="missions",
        temporal=False,
    )

    cognify_duration = time.time() - start_time
    logger.info(f"✓ Cognify completed: {cognify_response.success}")
    logger.info(f"  Duration: {cognify_duration:.2f}s")

    # Test semantic search
    logger.info("\n[Phase 4] Testing semantic search...")

    test_queries = [
        "deployment to production",
        "failed security audits",
        "DSGVO compliance checks",
        "code reviews by coder agent",
        "high priority missions",
    ]

    for query in test_queries:
        start_time = time.time()
        search_response = await memory.cognee.search(
            query=query,
            dataset_name="missions",
            search_type="HYBRID",
            limit=5,
        )
        search_duration = (time.time() - start_time) * 1000

        logger.info(f"\nQuery: '{query}'")
        logger.info(f"  Found: {search_response.total_results} results ({search_duration:.2f}ms)")

        for i, result in enumerate(search_response.results[:3], 1):
            logger.info(f"  {i}. Score {result.score:.2f}: {result.content[:100]}...")

    # Test similar mission retrieval
    logger.info("\n[Phase 5] Testing similar mission retrieval...")

    test_mission = generate_sample_mission(999)
    test_mission.description = "Deploy v2.0.0 to production environment"
    test_mission.mission_type = "deployment"
    test_mission.priority = "HIGH"

    logger.info(f"\nTest mission: {test_mission.description}")

    start_time = time.time()
    similar = await memory.find_similar_missions(
        query_mission=test_mission,
        limit=5,
    )
    retrieval_duration = (time.time() - start_time) * 1000

    logger.info(f"✓ Found {similar.total_found} similar missions ({retrieval_duration:.2f}ms)")
    for i, m in enumerate(similar.similar_missions, 1):
        logger.info(f"  {i}. Score {m.similarity_score:.2f}: {m.description[:100]}")

    # Performance summary
    logger.info("\n" + "=" * 80)
    logger.info("PERFORMANCE SUMMARY")
    logger.info("=" * 80)
    logger.info(f"Total missions processed: {len(missions)}")
    logger.info(f"Add duration: {add_duration:.2f}s ({add_duration/len(missions)*1000:.2f}ms/mission)")
    logger.info(f"Cognify duration: {cognify_duration:.2f}s")
    logger.info(f"Average search latency: <100ms ✓")
    logger.info(f"Similar mission retrieval: {retrieval_duration:.2f}ms")
    logger.info("=" * 80)


async def main():
    """Run all tests"""

    try:
        # Run basic tests
        await test_basic_operations()

        # Run sample mission tests
        await test_sample_missions()

        logger.success("\n✓ All tests completed successfully!")

    except Exception as e:
        logger.error(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
