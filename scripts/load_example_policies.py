#!/usr/bin/env python3
"""
Load Example Policies into Policy Engine

This script loads all pre-configured policy rules from example_policies.py
into the Policy Engine for production use.

Usage:
    python scripts/load_example_policies.py [--clear]

Options:
    --clear     Clear existing policies before loading
"""

import sys
import os
from pathlib import Path

# Add backend to path
BACKEND_DIR = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(BACKEND_DIR))

from backend.app.modules.policy.service import PolicyService
from backend.app.modules.policy.example_policies import (
    get_all_example_policies,
    get_policies_by_category,
    get_compliance_policies,
)


def main():
    """Main function to load policies."""
    import argparse

    parser = argparse.ArgumentParser(description="Load example policies")
    parser.add_argument(
        "--clear",
        action="store_true",
        help="Clear existing policies before loading"
    )
    parser.add_argument(
        "--category",
        type=str,
        help="Load only policies from specific category"
    )
    parser.add_argument(
        "--compliance",
        type=str,
        help="Load only policies for specific compliance framework (e.g., DSGVO)"
    )

    args = parser.parse_args()

    print("=" * 70)
    print("Loading Example Policies into Policy Engine")
    print("=" * 70)
    print()

    # Initialize policy service
    policy_service = PolicyService()

    # Clear existing policies if requested
    if args.clear:
        print("Clearing existing policies...")
        existing = policy_service.get_all_policies()
        for policy in existing:
            policy_service.delete_policy(policy.id)
        print(f"✓ Cleared {len(existing)} existing policies")
        print()

    # Determine which policies to load
    if args.category:
        policies = get_policies_by_category(args.category)
        print(f"Loading policies from category: {args.category}")
    elif args.compliance:
        policies = get_compliance_policies(args.compliance)
        print(f"Loading policies for compliance framework: {args.compliance}")
    else:
        policies = get_all_example_policies()
        print("Loading all example policies")

    print()

    # Load policies
    loaded_count = 0
    for policy in policies:
        try:
            policy_service.add_policy(policy)
            print(f"✓ Loaded: [{policy.priority}] {policy.name} ({policy.effect})")
            loaded_count += 1
        except Exception as e:
            print(f"✗ Failed to load {policy.name}: {e}")

    print()
    print("=" * 70)
    print(f"✓ Successfully loaded {loaded_count} policies")
    print("=" * 70)
    print()

    # Summary by category
    all_loaded = policy_service.get_all_policies()
    categories = {}
    for policy in all_loaded:
        cat = policy.metadata.get("category", "uncategorized")
        categories[cat] = categories.get(cat, 0) + 1

    print("Policies by category:")
    for category, count in sorted(categories.items()):
        print(f"  {category}: {count}")

    print()

    # Summary by priority
    print("Policies by priority:")
    for policy in sorted(all_loaded, key=lambda p: p.priority, reverse=True)[:10]:
        print(f"  [{policy.priority}] {policy.name}")

    print()
    print("Total policies in system:", len(all_loaded))


if __name__ == "__main__":
    main()
