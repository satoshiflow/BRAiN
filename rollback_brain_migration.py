#!/usr/bin/env python3
"""
BRAIN Migration Rollback Script
Restores previous configuration from backup file

Usage:
    python3 rollback_brain_migration.py --backup brain_backup_dev_20260107_123456.json --dry-run
    python3 rollback_brain_migration.py --backup brain_backup_dev_20260107_123456.json --execute

Features:
    - Restores domains from backup
    - Restores environment variables
    - Triggers redeploy if needed
    - Dry-run mode for safety
    - Detailed logging
"""

import os
import sys
import json
import time
import argparse
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from pathlib import Path

try:
    import requests
except ImportError:
    print("❌ Error: 'requests' library not found. Install with: pip install requests")
    sys.exit(1)


# ========================================
# COOLIFY API CLIENT
# ========================================

class CoolifyClient:
    """Coolify API Client with error handling."""

    def __init__(self, token: str, base_url: str = "https://coolify.falklabs.de"):
        self.token = token
        self.base_url = f"{base_url}/api/v1"
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

    def _request(self, method: str, endpoint: str, **kwargs) -> Tuple[bool, Optional[Dict]]:
        """Make API request with error handling."""
        url = f"{self.base_url}{endpoint}"

        try:
            response = requests.request(method, url, headers=self.headers, timeout=30, **kwargs)
            response.raise_for_status()
            return True, response.json()
        except requests.exceptions.HTTPError as e:
            print(f"❌ HTTP Error: {e}")
            print(f"Response: {response.text if 'response' in locals() else 'No response'}")
            return False, None
        except Exception as e:
            print(f"❌ Error: {e}")
            return False, None

    def update_domains(self, uuid: str, domains: List[str]) -> Tuple[bool, Optional[Dict]]:
        """Update application domains."""
        data = {"domains": ",".join(domains)}
        return self._request("PATCH", f"/applications/{uuid}", json=data)

    def update_env_variable(self, uuid: str, key: str, value: str) -> Tuple[bool, Optional[Dict]]:
        """Update single environment variable."""
        data = {"key": key, "value": value}
        return self._request("POST", f"/applications/{uuid}/envs", json=data)

    def restart_application(self, uuid: str) -> Tuple[bool, Optional[Dict]]:
        """Restart application."""
        return self._request("POST", f"/applications/{uuid}/restart")

    def redeploy_application(self, uuid: str) -> Tuple[bool, Optional[Dict]]:
        """Redeploy application."""
        return self._request("POST", f"/applications/{uuid}/deploy")


# ========================================
# ROLLBACK FUNCTIONS
# ========================================

class BrainRollback:
    """BRAIN Migration Rollback Orchestrator."""

    def __init__(self, coolify_client: CoolifyClient, backup_file: str, dry_run: bool = True):
        self.client = coolify_client
        self.backup_file = backup_file
        self.dry_run = dry_run
        self.backup_data = None

    def load_backup(self) -> bool:
        """Load backup file."""
        print(f"\n📁 Loading backup: {self.backup_file}")

        if not Path(self.backup_file).exists():
            print(f"❌ Backup file not found: {self.backup_file}")
            return False

        try:
            with open(self.backup_file, "r") as f:
                self.backup_data = json.load(f)

            print(f"✅ Backup loaded")
            print(f"   Timestamp: {self.backup_data.get('timestamp', 'unknown')}")
            print(f"   Environment: {self.backup_data.get('environment', 'unknown')}")
            print(f"   Applications: {len(self.backup_data.get('applications', {}))}")

            return True

        except Exception as e:
            print(f"❌ Error loading backup: {e}")
            return False

    def restore_service(self, service_name: str, service_data: Dict) -> bool:
        """Restore a single service from backup."""
        uuid = service_data.get("uuid")

        if not uuid:
            print(f"❌ No UUID found in backup for {service_name}")
            return False

        print(f"\n🔧 Restoring {service_name} ({uuid})...")

        # 1. Restore Domain
        domains = service_data.get("domains", [])
        if isinstance(domains, str):
            domains = [d.strip() for d in domains.split(",")]

        if domains:
            domain_str = ", ".join(domains)
            print(f"  📍 Domain: {domain_str}")

            if not self.dry_run:
                success, _ = self.client.update_domains(uuid, domains)
                if not success:
                    print(f"  ❌ Failed to restore domain")
                    return False
                print(f"  ✅ Domain restored")
            else:
                print(f"  🔍 DRY-RUN: Would restore domain: {domain_str}")

        # 2. Restore ENV Variables
        env_vars = service_data.get("environment_variables", {})

        if env_vars:
            print(f"  🔑 Environment Variables: {len(env_vars)} vars")

            for key, value in env_vars.items():
                if not self.dry_run:
                    success, _ = self.client.update_env_variable(uuid, key, value)
                    if not success:
                        print(f"  ⚠️  Warning: Failed to restore ENV {key}")
                    else:
                        print(f"  ✅ Restored: {key}")
                else:
                    print(f"  🔍 DRY-RUN: Would restore {key}")

        # 3. Restart or Redeploy
        needs_rebuild = "build_args" in service_data or "buildpack" in service_data

        if needs_rebuild:
            print(f"  🏗️  Triggering redeploy...")

            if not self.dry_run:
                success, _ = self.client.redeploy_application(uuid)
                if not success:
                    print(f"  ⚠️  Warning: Redeploy failed")
                else:
                    print(f"  ✅ Redeploy triggered")
            else:
                print(f"  🔍 DRY-RUN: Would trigger redeploy")
        else:
            if not self.dry_run:
                print(f"  🔄 Restarting {service_name}...")
                success, _ = self.client.restart_application(uuid)
                if success:
                    print(f"  ✅ Restart triggered")
                else:
                    print(f"  ⚠️  Warning: Restart failed")
            else:
                print(f"  🔍 DRY-RUN: Would restart")

        return True

    def rollback_all(self) -> bool:
        """Rollback all services."""
        print(f"\n{'='*60}")
        print(f"🔙 BRAIN Migration Rollback")
        print(f"Backup: {self.backup_file}")
        print(f"Mode: {'DRY-RUN (no changes)' if self.dry_run else 'EXECUTE (live changes)'}")
        print(f"{'='*60}")

        # Load backup
        if not self.load_backup():
            return False

        # Get applications from backup
        applications = self.backup_data.get("applications", {})

        if not applications:
            print("❌ No applications found in backup")
            return False

        # Restore services (order matters: backend first)
        service_order = ["backend", "control_deck", "axe_ui"]

        for service in service_order:
            if service in applications:
                if not self.restore_service(service, applications[service]):
                    print(f"\n❌ Rollback failed at: {service}")
                    return False

                # Wait between services
                if not self.dry_run:
                    print("  ⏳ Waiting 5 seconds before next service...")
                    time.sleep(5)
            else:
                print(f"⚠️  Service '{service}' not found in backup")

        # Restore other services
        for service, data in applications.items():
            if service not in service_order:
                print(f"\n⚠️  Found additional service in backup: {service}")
                if not self.dry_run:
                    restore = input("  Restore this service? (y/n): ")
                    if restore.lower() == 'y':
                        self.restore_service(service, data)

        # Success
        print(f"\n{'='*60}")
        if self.dry_run:
            print("✅ ROLLBACK DRY-RUN COMPLETE - No changes made")
            print("   Run with --execute to apply rollback")
        else:
            print("✅ ROLLBACK COMPLETE")
            print("   Run validation script to verify deployment")
        print(f"{'='*60}")

        return True


# ========================================
# MAIN CLI
# ========================================

def main():
    parser = argparse.ArgumentParser(
        description="BRAIN Migration Rollback Script",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Dry-run rollback
  python3 rollback_brain_migration.py --backup brain_backup_dev_20260107.json --dry-run

  # Execute rollback
  python3 rollback_brain_migration.py --backup brain_backup_dev_20260107.json --execute
        """
    )

    parser.add_argument(
        "--backup",
        required=True,
        help="Backup file to restore from"
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help="Dry-run mode (no changes, just preview)"
    )

    parser.add_argument(
        "--execute",
        action="store_true",
        default=False,
        help="Execute rollback (makes actual changes)"
    )

    parser.add_argument(
        "--token",
        help="Coolify API token (or set COOLIFY_TOKEN env var)"
    )

    parser.add_argument(
        "--coolify-url",
        default="https://coolify.falklabs.de",
        help="Coolify URL (default: https://coolify.falklabs.de)"
    )

    args = parser.parse_args()

    # Validate mode
    if args.dry_run and args.execute:
        print("❌ Error: Cannot use both --dry-run and --execute")
        sys.exit(1)

    if not args.dry_run and not args.execute:
        print("❌ Error: Must specify either --dry-run or --execute")
        sys.exit(1)

    # Get API token
    token = args.token or os.getenv("COOLIFY_TOKEN")
    if not token:
        print("❌ Error: Coolify API token not provided")
        print("   Set COOLIFY_TOKEN env var or use --token parameter")
        sys.exit(1)

    # Safety check
    if args.execute:
        print("\n⚠️  WARNING: You are about to rollback to previous configuration!")
        print(f"   Backup file: {args.backup}")
        print("   This will revert recent changes.")
        print("   Type 'ROLLBACK' to confirm:")

        if input().strip() != "ROLLBACK":
            print("❌ Rollback cancelled")
            sys.exit(0)

    # Initialize
    dry_run = args.dry_run or not args.execute
    client = CoolifyClient(token, args.coolify_url)
    rollback = BrainRollback(client, args.backup, dry_run=dry_run)

    # Run rollback
    try:
        success = rollback.rollback_all()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n❌ Rollback interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Rollback failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
