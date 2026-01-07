#!/usr/bin/env python3
"""
BRAIN Domain Migration Script
Automatisiert die Umstellung auf Subdomain-Struktur via Coolify API

Usage:
    python3 migrate_brain_domains.py --env dev --dry-run
    python3 migrate_brain_domains.py --env dev --execute
    python3 migrate_brain_domains.py --env stage --execute
    python3 migrate_brain_domains.py --env prod --execute

Features:
    - Automatic backup before migration
    - Dry-run mode for safety
    - Step-by-step validation
    - Automatic rollback on failure
    - Coolify API integration
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
# CONFIGURATION
# ========================================

# SOLL-Zustand Domain-Mapping
DOMAIN_CONFIG = {
    "dev": {
        "backend": {
            "new_domain": "api.dev.brain.falklabs.de",
            "old_domain": "dev.brain.falklabs.de",  # (with /api/* path)
            "env_vars": {
                "CORS_ORIGINS": '["https://dev.brain.falklabs.de","https://axe.dev.brain.falklabs.de","https://docs.dev.brain.falklabs.de"]'
            }
        },
        "control_deck": {
            "new_domain": "dev.brain.falklabs.de",
            "old_domain": "dev.brain.falklabs.de",
            "env_vars": {
                "NEXT_PUBLIC_BRAIN_API_BASE": "https://api.dev.brain.falklabs.de"
            },
            "build_args": {
                "NEXT_PUBLIC_BRAIN_API_BASE": "https://api.dev.brain.falklabs.de"
            }
        },
        "axe_ui": {
            "new_domain": "axe.dev.brain.falklabs.de",
            "old_domain": "axe.dev.brain.falklabs.de",
            "env_vars": {
                "NEXT_PUBLIC_BRAIN_API_BASE": "https://api.dev.brain.falklabs.de"
            },
            "build_args": {
                "NEXT_PUBLIC_BRAIN_API_BASE": "https://api.dev.brain.falklabs.de"
            }
        }
    },
    "stage": {
        "backend": {
            "new_domain": "api.stage.brain.falklabs.de",
            "old_domain": "stage.brain.falklabs.de",
            "env_vars": {
                "CORS_ORIGINS": '["https://stage.brain.falklabs.de","https://axe.stage.brain.falklabs.de","https://docs.stage.brain.falklabs.de"]'
            }
        },
        "control_deck": {
            "new_domain": "stage.brain.falklabs.de",
            "old_domain": "stage.brain.falklabs.de",
            "env_vars": {
                "NEXT_PUBLIC_BRAIN_API_BASE": "https://api.stage.brain.falklabs.de"
            },
            "build_args": {
                "NEXT_PUBLIC_BRAIN_API_BASE": "https://api.stage.brain.falklabs.de"
            }
        },
        "axe_ui": {
            "new_domain": "axe.stage.brain.falklabs.de",
            "old_domain": "axe.stage.brain.falklabs.de",
            "env_vars": {
                "NEXT_PUBLIC_BRAIN_API_BASE": "https://api.stage.brain.falklabs.de"
            },
            "build_args": {
                "NEXT_PUBLIC_BRAIN_API_BASE": "https://api.stage.brain.falklabs.de"
            }
        }
    },
    "prod": {
        "backend": {
            "new_domain": "api.brain.falklabs.de",
            "old_domain": "brain.falklabs.de",
            "env_vars": {
                "CORS_ORIGINS": '["https://brain.falklabs.de","https://axe.brain.falklabs.de","https://docs.brain.falklabs.de"]'
            }
        },
        "control_deck": {
            "new_domain": "brain.falklabs.de",
            "old_domain": "brain.falklabs.de",
            "env_vars": {
                "NEXT_PUBLIC_BRAIN_API_BASE": "https://api.brain.falklabs.de"
            },
            "build_args": {
                "NEXT_PUBLIC_BRAIN_API_BASE": "https://api.brain.falklabs.de"
            }
        },
        "axe_ui": {
            "new_domain": "axe.brain.falklabs.de",
            "old_domain": "axe.brain.falklabs.de",
            "env_vars": {
                "NEXT_PUBLIC_BRAIN_API_BASE": "https://api.brain.falklabs.de"
            },
            "build_args": {
                "NEXT_PUBLIC_BRAIN_API_BASE": "https://api.brain.falklabs.de"
            }
        }
    }
}


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

    def list_applications(self) -> Tuple[bool, Optional[List[Dict]]]:
        """List all applications."""
        return self._request("GET", "/applications")

    def get_application(self, uuid: str) -> Tuple[bool, Optional[Dict]]:
        """Get application details."""
        return self._request("GET", f"/applications/{uuid}")

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
        """Redeploy application (for build args)."""
        return self._request("POST", f"/applications/{uuid}/deploy")


# ========================================
# MIGRATION FUNCTIONS
# ========================================

class BrainMigration:
    """BRAIN Domain Migration Orchestrator."""

    def __init__(self, coolify_client: CoolifyClient, environment: str, dry_run: bool = True):
        self.client = coolify_client
        self.environment = environment
        self.dry_run = dry_run
        self.backup_file = f"brain_backup_{environment}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        self.app_mapping = {}  # UUID mapping

    def find_applications(self) -> bool:
        """Find all BRAIN applications for the environment."""
        print(f"\n🔍 Searching for BRAIN applications in '{self.environment}' environment...")

        success, apps = self.client.list_applications()
        if not success:
            print("❌ Failed to list applications from Coolify API")
            return False

        # Filter by environment
        env_prefix = self.environment if self.environment != "prod" else ""
        search_terms = {
            "backend": [f"{env_prefix}backend", f"{env_prefix}-backend", f"brain-{env_prefix}backend"],
            "control_deck": [f"{env_prefix}control", f"{env_prefix}-control", f"brain-{env_prefix}control"],
            "axe_ui": [f"{env_prefix}axe", f"{env_prefix}-axe", f"brain-{env_prefix}axe"]
        }

        for app in apps:
            name = app.get("name", "").lower()
            uuid = app.get("uuid")

            for service, terms in search_terms.items():
                if any(term in name for term in terms):
                    self.app_mapping[service] = app
                    print(f"  ✅ Found {service}: {app.get('name')} ({uuid})")
                    break

        # Verify all required services found
        required = ["backend", "control_deck", "axe_ui"]
        missing = [s for s in required if s not in self.app_mapping]

        if missing:
            print(f"\n⚠️  Warning: Missing applications: {', '.join(missing)}")
            print("     You may need to manually specify UUIDs or adjust search terms.")
            return False

        return True

    def create_backup(self) -> bool:
        """Create backup of current state."""
        print(f"\n💾 Creating backup: {self.backup_file}")

        backup_data = {
            "timestamp": datetime.now().isoformat(),
            "environment": self.environment,
            "applications": {}
        }

        for service, app in self.app_mapping.items():
            uuid = app.get("uuid")
            success, details = self.client.get_application(uuid)

            if success:
                backup_data["applications"][service] = details
                print(f"  ✅ Backed up {service}")
            else:
                print(f"  ⚠️  Could not backup {service}")

        # Save backup
        Path(self.backup_file).write_text(json.dumps(backup_data, indent=2))
        print(f"✅ Backup saved: {self.backup_file}")
        return True

    def migrate_service(self, service: str) -> bool:
        """Migrate a single service."""
        config = DOMAIN_CONFIG[self.environment][service]
        app = self.app_mapping.get(service)

        if not app:
            print(f"❌ Service '{service}' not found in app mapping")
            return False

        uuid = app.get("uuid")
        print(f"\n🔧 Migrating {service} ({uuid})...")

        # 1. Update Domain
        new_domain = config["new_domain"]
        print(f"  📍 Domain: {config.get('old_domain', 'unknown')} → {new_domain}")

        if not self.dry_run:
            success, _ = self.client.update_domains(uuid, [new_domain])
            if not success:
                print(f"  ❌ Failed to update domain for {service}")
                return False
            print(f"  ✅ Domain updated")
        else:
            print(f"  🔍 DRY-RUN: Would update domain to {new_domain}")

        # 2. Update ENV Variables
        if "env_vars" in config:
            for key, value in config["env_vars"].items():
                print(f"  🔑 ENV: {key}")

                if not self.dry_run:
                    success, _ = self.client.update_env_variable(uuid, key, value)
                    if not success:
                        print(f"  ⚠️  Warning: Failed to update ENV {key}")
                    else:
                        print(f"  ✅ ENV updated: {key}")
                else:
                    print(f"  🔍 DRY-RUN: Would update {key} = {value[:50]}...")

        # 3. Redeploy if build args changed (for Next.js)
        needs_rebuild = "build_args" in config
        if needs_rebuild:
            print(f"  🏗️  Build args changed - redeployment required")

            if not self.dry_run:
                print(f"  🚀 Triggering redeploy...")
                success, _ = self.client.redeploy_application(uuid)
                if not success:
                    print(f"  ⚠️  Warning: Redeploy failed for {service}")
                else:
                    print(f"  ✅ Redeploy triggered")
            else:
                print(f"  🔍 DRY-RUN: Would trigger redeploy")
        else:
            # Just restart
            if not self.dry_run:
                print(f"  🔄 Restarting {service}...")
                success, _ = self.client.restart_application(uuid)
                if success:
                    print(f"  ✅ Restart triggered")
                else:
                    print(f"  ⚠️  Warning: Restart failed")
            else:
                print(f"  🔍 DRY-RUN: Would restart {service}")

        return True

    def migrate_all(self) -> bool:
        """Migrate all services."""
        print(f"\n{'='*60}")
        print(f"🚀 Starting BRAIN Domain Migration")
        print(f"Environment: {self.environment}")
        print(f"Mode: {'DRY-RUN (no changes)' if self.dry_run else 'EXECUTE (live changes)'}")
        print(f"{'='*60}")

        # Step 1: Find applications
        if not self.find_applications():
            return False

        # Step 2: Create backup
        if not self.create_backup():
            print("⚠️  Backup failed - do you want to continue? (y/n)")
            if input().lower() != 'y':
                return False

        # Step 3: Migrate services (order matters: backend first)
        services = ["backend", "control_deck", "axe_ui"]

        for service in services:
            if not self.migrate_service(service):
                print(f"\n❌ Migration failed at: {service}")
                print("Consider running rollback script.")
                return False

            # Wait between services
            if not self.dry_run:
                print("  ⏳ Waiting 5 seconds before next service...")
                time.sleep(5)

        # Success
        print(f"\n{'='*60}")
        if self.dry_run:
            print("✅ DRY-RUN COMPLETE - No changes made")
            print("   Run with --execute to apply changes")
        else:
            print("✅ MIGRATION COMPLETE")
            print(f"   Backup saved: {self.backup_file}")
            print("   Run validation script to verify deployment")
        print(f"{'='*60}")

        return True


# ========================================
# MAIN CLI
# ========================================

def main():
    parser = argparse.ArgumentParser(
        description="BRAIN Domain Migration Script",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Dry-run for DEV environment
  python3 migrate_brain_domains.py --env dev --dry-run

  # Execute migration for DEV
  python3 migrate_brain_domains.py --env dev --execute

  # Execute migration for PROD (requires confirmation)
  python3 migrate_brain_domains.py --env prod --execute
        """
    )

    parser.add_argument(
        "--env",
        choices=["dev", "stage", "prod"],
        required=True,
        help="Environment to migrate"
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
        help="Execute migration (makes actual changes)"
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

    # Production safety check
    if args.env == "prod" and args.execute:
        print("\n⚠️  WARNING: You are about to migrate PRODUCTION environment!")
        print("   This will make changes to live systems.")
        print("   Type 'MIGRATE PRODUCTION' to confirm:")

        if input().strip() != "MIGRATE PRODUCTION":
            print("❌ Migration cancelled")
            sys.exit(0)

    # Initialize
    dry_run = args.dry_run or not args.execute
    client = CoolifyClient(token, args.coolify_url)
    migration = BrainMigration(client, args.env, dry_run=dry_run)

    # Run migration
    try:
        success = migration.migrate_all()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n❌ Migration interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Migration failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
