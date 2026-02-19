#!/usr/bin/env python3
"""
Deploy Control Deck to Coolify with proper environment variables
Domain: falklabs.de
"""
import os
import sys
import json
import secrets
from coolify_manager import CoolifyManager

# Configuration
DOMAIN = "falklabs.de"
PRODUCTION_API_URL = f"https://brain-api.{DOMAIN}"

def generate_auth_secret():
    """Generate a secure AUTH_SECRET (32+ characters)"""
    return secrets.token_urlsafe(48)  # Generates ~64 character string

def find_control_deck_app(manager: CoolifyManager):
    """Find Control Deck application UUID"""
    print("🔍 Searching for Control Deck application...")

    apps = manager.list_applications()

    # Search for control deck app
    control_deck = None
    for app in apps:
        name = app.get("name", "").lower()
        if "control" in name or "deck" in name:
            control_deck = app
            print(f"✅ Found: {app.get('name')} (UUID: {app.get('uuid')})")
            break

    if not control_deck:
        print("❌ Control Deck application not found!")
        print("\nAvailable applications:")
        for app in apps:
            print(f"  - {app.get('name')} ({app.get('uuid')})")
        sys.exit(1)

    return control_deck

def update_environment_variables(manager: CoolifyManager, app_uuid: str, auth_secret: str):
    """Update environment variables for Control Deck"""
    print("\n📝 Updating environment variables...")

    env_vars = {
        "AUTH_SECRET": auth_secret,
        "NEXT_PUBLIC_BRAIN_API_BASE": PRODUCTION_API_URL,
        "NODE_ENV": "production",
        "NEXT_TELEMETRY_DISABLED": "1",
    }

    for key, value in env_vars.items():
        try:
            print(f"  Setting {key}...")
            manager.update_env(app_uuid, key, value)
        except Exception as e:
            print(f"  ⚠️  Warning: Could not set {key}: {e}")
            print(f"     You may need to set this manually in Coolify UI")

    print("✅ Environment variables updated")

def update_build_args(manager: CoolifyManager, app_uuid: str):
    """Update build arguments (if supported by API)"""
    print("\n🔨 Build arguments to set in Coolify UI:")
    print(f"  NEXT_PUBLIC_BRAIN_API_BASE={PRODUCTION_API_URL}")
    print("\n  → Go to Coolify → Application → Build Configuration → Build Arguments")

def trigger_deployment(manager: CoolifyManager, app_uuid: str):
    """Trigger a new deployment"""
    print("\n🚀 Triggering deployment...")

    try:
        result = manager.restart_application(app_uuid)
        print("✅ Deployment triggered successfully!")
        print(f"   Check status at: https://coolify.{DOMAIN}/application/{app_uuid}")
        return result
    except Exception as e:
        print(f"⚠️  Could not trigger deployment: {e}")
        print("   → Manually deploy via Coolify UI")

def main():
    """Main deployment flow"""
    print("=" * 70)
    print("Control Deck Deployment to Coolify")
    print(f"Domain: {DOMAIN}")
    print(f"API URL: {PRODUCTION_API_URL}")
    print("=" * 70)

    # Get Coolify token
    token = os.getenv("COOLIFY_TOKEN")
    if not token:
        print("\n❌ COOLIFY_TOKEN not set!")
        print("\nTo get your token:")
        print("  1. Login to https://coolify.falklabs.de")
        print("  2. Go to Settings → API Tokens")
        print("  3. Create new token")
        print("  4. Export: export COOLIFY_TOKEN='your-token-here'")
        print("  5. Run this script again")
        sys.exit(1)

    try:
        manager = CoolifyManager(token=token, url=f"https://coolify.{DOMAIN}")

        # Find Control Deck app
        app = find_control_deck_app(manager)
        app_uuid = app.get("uuid")
        app_name = app.get("name")

        print(f"\n📦 Target Application:")
        print(f"   Name: {app_name}")
        print(f"   UUID: {app_uuid}")

        # Generate AUTH_SECRET
        auth_secret = generate_auth_secret()
        print(f"\n🔐 Generated AUTH_SECRET (save this!):")
        print(f"   {auth_secret}")

        # Save to file for reference
        with open("control_deck_auth_secret.txt", "w") as f:
            f.write(f"AUTH_SECRET={auth_secret}\n")
            f.write(f"Generated on: {__import__('datetime').datetime.now()}\n")
        print(f"   ✅ Saved to: control_deck_auth_secret.txt")

        # Update environment variables
        update_environment_variables(manager, app_uuid, auth_secret)

        # Show build args instructions
        update_build_args(manager, app_uuid)

        # Ask for confirmation
        print("\n" + "=" * 70)
        response = input("\n🤔 Ready to deploy? This will restart the application. (y/N): ")

        if response.lower() != 'y':
            print("❌ Deployment cancelled.")
            print("\n💡 To deploy manually:")
            print(f"   1. Go to https://coolify.{DOMAIN}/application/{app_uuid}")
            print("   2. Set Build Args: NEXT_PUBLIC_BRAIN_API_BASE")
            print("   3. Click 'Deploy'")
            sys.exit(0)

        # Trigger deployment
        trigger_deployment(manager, app_uuid)

        print("\n" + "=" * 70)
        print("✅ DEPLOYMENT COMPLETE!")
        print("=" * 70)
        print("\n📋 Next Steps:")
        print(f"   1. Monitor deployment at: https://coolify.{DOMAIN}/application/{app_uuid}")
        print(f"   2. Check deployment logs for errors")
        print(f"   3. Test application at: https://control-deck.{DOMAIN}")
        print(f"   4. Verify AXE pages: https://control-deck.{DOMAIN}/axe/identity")
        print("\n🔐 Important:")
        print("   - AUTH_SECRET saved in: control_deck_auth_secret.txt")
        print("   - Keep this file secure!")
        print("   - Add to your password manager")

    except Exception as e:
        print(f"\n❌ Deployment failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
