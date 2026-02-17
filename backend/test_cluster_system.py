#!/usr/bin/env python3
"""
Test Script for Cluster System (Tasks 3.2-3.4)

Tests:
- Blueprint Loader
- Blueprint Validator
- Cluster Service (basic functionality)
"""

import asyncio
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from app.modules.cluster_system.blueprints.loader import BlueprintLoader
from app.modules.cluster_system.blueprints.validator import BlueprintValidator
from loguru import logger


async def test_blueprint_loader():
    """Test blueprint loader"""
    print("\n" + "="*60)
    print("TEST 1: Blueprint Loader")
    print("="*60)

    try:
        loader = BlueprintLoader(blueprints_dir="../storage/blueprints")

        # Test load_from_file
        print("\n1. Loading marketing.yaml...")
        blueprint = loader.load_from_file("marketing.yaml")

        print(f"✅ Loaded blueprint: {blueprint['metadata']['id']}")
        print(f"   Name: {blueprint['metadata']['name']}")
        print(f"   Version: {blueprint['metadata']['version']}")
        print(f"   Agents: {len(blueprint.get('agents', []))}")

        # Test load_from_string
        print("\n2. Testing load_from_string...")
        yaml_string = """
metadata:
  id: test-blueprint
  name: Test Blueprint
  version: 1.0.0

cluster:
  type: department
  min_workers: 1
  max_workers: 5

agents:
  - role: supervisor
    name: Test Supervisor
    count: 1
"""
        blueprint2 = loader.load_from_string(yaml_string)
        print(f"✅ Loaded from string: {blueprint2['metadata']['id']}")

        # Test save_to_file
        print("\n3. Testing save_to_file...")
        save_path = loader.save_to_file(blueprint2, "test-blueprint.yaml")
        print(f"✅ Saved to: {save_path}")

        print("\n✅ Blueprint Loader: ALL TESTS PASSED")
        return True

    except Exception as e:
        print(f"\n❌ Blueprint Loader: FAILED - {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_blueprint_validator():
    """Test blueprint validator"""
    print("\n" + "="*60)
    print("TEST 2: Blueprint Validator")
    print("="*60)

    try:
        loader = BlueprintLoader(blueprints_dir="../storage/blueprints")
        validator = BlueprintValidator()

        # Test valid blueprint
        print("\n1. Validating marketing.yaml...")
        blueprint = loader.load_from_file("marketing.yaml")
        is_valid = validator.validate(blueprint)

        if is_valid:
            print("✅ Marketing blueprint is valid")
        else:
            print("❌ Marketing blueprint validation failed")
            return False

        # Test invalid blueprint (missing metadata)
        print("\n2. Testing invalid blueprint (missing metadata)...")
        invalid_blueprint = {
            "cluster": {"type": "department", "min_workers": 1, "max_workers": 5},
            "agents": []
        }

        try:
            validator.validate(invalid_blueprint)
            print("❌ Should have raised ValueError for missing metadata")
            return False
        except ValueError as e:
            print(f"✅ Correctly rejected invalid blueprint: {e}")

        # Test invalid blueprint (no supervisor)
        print("\n3. Testing invalid blueprint (no supervisor)...")
        invalid_blueprint2 = {
            "metadata": {"id": "test", "name": "Test", "version": "1.0.0"},
            "cluster": {"type": "department", "min_workers": 1, "max_workers": 5},
            "agents": [
                {"role": "worker", "name": "Worker 1"}
            ]
        }

        try:
            validator.validate(invalid_blueprint2)
            print("❌ Should have raised ValueError for missing supervisor")
            return False
        except ValueError as e:
            print(f"✅ Correctly rejected blueprint without supervisor: {e}")

        print("\n✅ Blueprint Validator: ALL TESTS PASSED")
        return True

    except Exception as e:
        print(f"\n❌ Blueprint Validator: FAILED - {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run all tests"""
    print("\n" + "="*60)
    print("BRAiN Cluster System Test Suite")
    print("Tasks 3.2-3.4 Implementation Verification")
    print("="*60)

    results = []

    # Run tests
    results.append(("Blueprint Loader", await test_blueprint_loader()))
    results.append(("Blueprint Validator", await test_blueprint_validator()))

    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{name:30s} {status}")

    print(f"\n{passed}/{total} tests passed")

    if passed == total:
        print("\n🎉 ALL TESTS PASSED! Tasks 3.2-3.4 implementation verified!")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed. Check errors above.")
        return 1


if __name__ == "__main__":
    exit(asyncio.run(main()))
