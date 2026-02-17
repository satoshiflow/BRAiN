#!/usr/bin/env python3
"""
Coolify API Manager for BRAIN Migration
"""
import os
import sys
import json
import requests
from typing import Dict, List, Optional
from datetime import datetime

class CoolifyManager:
    def __init__(self, token: str = None, url: str = None):
        self.token = token or os.getenv("COOLIFY_TOKEN")
        self.url = url or os.getenv("COOLIFY_URL", "https://coolify.falklabs.de")

        if not self.token:
            raise ValueError("Coolify token not provided. Set COOLIFY_TOKEN env var or pass token parameter.")

        self.base_url = f"{self.url}/api/v1"
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

    def _request(self, method: str, endpoint: str, **kwargs) -> Dict:
        """Make API request with error handling."""
        url = f"{self.base_url}{endpoint}"

        try:
            response = requests.request(method, url, headers=self.headers, **kwargs)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            print(f"❌ HTTP Error: {e}")
            print(f"Response: {response.text}")
            raise
        except Exception as e:
            print(f"❌ Error: {e}")
            raise

    def list_applications(self) -> List[Dict]:
        """List all applications."""
        return self._request("GET", "/applications")

    def get_application(self, uuid: str) -> Dict:
        """Get application details."""
        return self._request("GET", f"/applications/{uuid}")

    def update_domains(self, uuid: str, domains: List[str]) -> Dict:
        """Update application domains."""
        data = {"domains": ",".join(domains)}
        return self._request("PATCH", f"/applications/{uuid}", json=data)

    def update_env(self, uuid: str, key: str, value: str) -> Dict:
        """Update environment variable."""
        data = {"key": key, "value": value}
        return self._request("POST", f"/applications/{uuid}/envs", json=data)

    def restart_application(self, uuid: str) -> Dict:
        """Restart application."""
        return self._request("POST", f"/applications/{uuid}/restart")

    def find_brain_apps(self) -> Dict:
        """Find all BRAIN-related applications."""
        apps = self.list_applications()
        brain_apps = {
            "dev": {},
            "prod": {},
            "stage": {},
            "unknown": []
        }

        for app in apps:
            name = app.get("name", "").lower()
            uuid = app.get("uuid")

            # Classify by environment
            if "brain" in name or "axe" in name or "control" in name:
                if "dev" in name:
                    env = "dev"
                elif "prod" in name:
                    env = "prod"
                elif "stage" in name:
                    env = "stage"
                else:
                    brain_apps["unknown"].append(app)
                    continue

                # Classify by service type
                if "backend" in name or "api" in name:
                    brain_apps[env]["backend"] = app
                elif "control" in name or "deck" in name:
                    brain_apps[env]["controldeck"] = app
                elif "axe" in name:
                    brain_apps[env]["axe_ui"] = app
                else:
                    if "other" not in brain_apps[env]:
                        brain_apps[env]["other"] = []
                    brain_apps[env]["other"].append(app)

        return brain_apps

    def export_current_state(self, output_file: str = None) -> Dict:
        """Export current state of all BRAIN apps."""
        if output_file is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"brain_backup_{timestamp}.json"

        brain_apps = self.find_brain_apps()

        # Enrich with full details
        for env in ["dev", "prod", "stage"]:
            for service, app in brain_apps[env].items():
                if isinstance(app, dict) and "uuid" in app:
                    uuid = app["uuid"]
                    try:
                        full_details = self.get_application(uuid)
                        brain_apps[env][service] = full_details
                    except Exception as e:
                        print(f"⚠️  Could not fetch details for {service} ({uuid}): {e}")

        with open(output_file, "w") as f:
            json.dump(brain_apps, f, indent=2)

        print(f"✅ Backup saved to: {output_file}")
        return brain_apps


def main():
    """CLI interface."""
    import argparse

    parser = argparse.ArgumentParser(description="Coolify Manager for BRAIN")
    parser.add_argument("--token", help="Coolify API token")
    parser.add_argument("--url", help="Coolify URL", default="https://coolify.falklabs.de")

    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # List apps
    subparsers.add_parser("list", help="List all BRAIN applications")

    # Export state
    export_parser = subparsers.add_parser("export", help="Export current state")
    export_parser.add_argument("--output", help="Output file", default=None)

    # Get app
    get_parser = subparsers.add_parser("get", help="Get application details")
    get_parser.add_argument("uuid", help="Application UUID")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    try:
        manager = CoolifyManager(token=args.token, url=args.url)

        if args.command == "list":
            apps = manager.find_brain_apps()
            print(json.dumps(apps, indent=2))

        elif args.command == "export":
            manager.export_current_state(args.output)

        elif args.command == "get":
            app = manager.get_application(args.uuid)
            print(json.dumps(app, indent=2))

    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
