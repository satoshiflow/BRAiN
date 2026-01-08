#!/usr/bin/env python3
"""
BRAIN Deployment Validation Script
Validates all domains, endpoints, SSL certificates, and CORS configuration

Usage:
    python3 validate_brain_deployment.py --env dev
    python3 validate_brain_deployment.py --env prod --full

Features:
    - HTTP/HTTPS health checks
    - SSL certificate validation
    - CORS policy testing
    - API endpoint verification
    - Response time measurement
    - Detailed error reporting
"""

import sys
import time
import argparse
import json
from typing import Dict, List, Tuple, Optional
from datetime import datetime
from urllib.parse import urlparse

try:
    import requests
    from requests.packages.urllib3.exceptions import InsecureRequestWarning
    requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
except ImportError:
    print("❌ Error: 'requests' library not found. Install with: pip install requests")
    sys.exit(1)


# ========================================
# CONFIGURATION
# ========================================

DOMAIN_CONFIG = {
    "dev": {
        "backend": "https://api.dev.brain.falklabs.de",
        "control_deck": "https://dev.brain.falklabs.de",
        "axe_ui": "https://axe.dev.brain.falklabs.de",
        "docs": "https://api.dev.brain.falklabs.de/docs"
    },
    "stage": {
        "backend": "https://api.stage.brain.falklabs.de",
        "control_deck": "https://stage.brain.falklabs.de",
        "axe_ui": "https://axe.stage.brain.falklabs.de",
        "docs": "https://api.stage.brain.falklabs.de/docs"
    },
    "prod": {
        "backend": "https://api.brain.falklabs.de",
        "control_deck": "https://brain.falklabs.de",
        "axe_ui": "https://axe.brain.falklabs.de",
        "docs": "https://api.brain.falklabs.de/docs"
    }
}

# API endpoints to test
API_ENDPOINTS = [
    "/health",
    "/api/health",
    "/docs",
    "/redoc",
    "/openapi.json"
]


# ========================================
# VALIDATION FUNCTIONS
# ========================================

class BrainValidator:
    """BRAIN Deployment Validator."""

    def __init__(self, environment: str, timeout: int = 10):
        self.environment = environment
        self.timeout = timeout
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "environment": environment,
            "checks": {},
            "summary": {
                "total": 0,
                "passed": 0,
                "failed": 0,
                "warnings": 0
            }
        }

    def check_http_status(self, url: str, expected_status: int = 200) -> Tuple[bool, str, Optional[float]]:
        """Check HTTP status code."""
        try:
            start_time = time.time()
            response = requests.get(url, timeout=self.timeout, allow_redirects=True, verify=True)
            elapsed = (time.time() - start_time) * 1000  # ms

            if response.status_code == expected_status:
                return True, f"OK ({response.status_code}) - {elapsed:.0f}ms", elapsed
            else:
                return False, f"Wrong status: {response.status_code} (expected {expected_status})", elapsed

        except requests.exceptions.SSLError as e:
            return False, f"SSL Error: {e}", None
        except requests.exceptions.Timeout:
            return False, f"Timeout (>{self.timeout}s)", None
        except requests.exceptions.ConnectionError as e:
            return False, f"Connection Error: {e}", None
        except Exception as e:
            return False, f"Error: {e}", None

    def check_ssl_certificate(self, url: str) -> Tuple[bool, str]:
        """Verify SSL certificate is valid."""
        try:
            response = requests.get(url, timeout=self.timeout, verify=True)
            return True, "Valid SSL certificate"
        except requests.exceptions.SSLError as e:
            return False, f"SSL certificate invalid: {e}"
        except Exception as e:
            return False, f"Error checking SSL: {e}"

    def check_cors_headers(self, url: str, origin: str) -> Tuple[bool, str]:
        """Check CORS headers."""
        try:
            headers = {"Origin": origin}
            response = requests.options(url, headers=headers, timeout=self.timeout)

            cors_header = response.headers.get("Access-Control-Allow-Origin")

            if cors_header:
                if cors_header == origin or cors_header == "*":
                    return True, f"CORS OK: {cors_header}"
                else:
                    return False, f"CORS mismatch: got {cors_header}, expected {origin}"
            else:
                return False, "No CORS headers found"

        except Exception as e:
            return False, f"Error checking CORS: {e}"

    def check_api_endpoints(self, base_url: str) -> Dict[str, Tuple[bool, str]]:
        """Check all API endpoints."""
        results = {}

        for endpoint in API_ENDPOINTS:
            url = f"{base_url}{endpoint}"
            success, message, elapsed = self.check_http_status(url)
            results[endpoint] = (success, message)

        return results

    def validate_service(self, service_name: str, url: str, full_check: bool = False) -> Dict:
        """Validate a single service."""
        print(f"\n🔍 Validating {service_name}: {url}")

        result = {
            "url": url,
            "checks": {},
            "status": "unknown"
        }

        # 1. Basic HTTP check
        print(f"  📡 HTTP Status...", end=" ")
        success, message, elapsed = self.check_http_status(url)
        result["checks"]["http"] = {"success": success, "message": message, "elapsed_ms": elapsed}

        if success:
            print(f"✅ {message}")
        else:
            print(f"❌ {message}")

        # 2. SSL certificate
        if url.startswith("https://"):
            print(f"  🔒 SSL Certificate...", end=" ")
            success, message = self.check_ssl_certificate(url)
            result["checks"]["ssl"] = {"success": success, "message": message}

            if success:
                print(f"✅ {message}")
            else:
                print(f"❌ {message}")

        # 3. CORS (only for backend)
        if "backend" in service_name or "api" in service_name:
            config = DOMAIN_CONFIG[self.environment]
            frontend_url = config.get("control_deck", "")

            if frontend_url:
                print(f"  🌐 CORS Headers...", end=" ")
                success, message = self.check_cors_headers(url, frontend_url)
                result["checks"]["cors"] = {"success": success, "message": message}

                if success:
                    print(f"✅ {message}")
                else:
                    print(f"⚠️  {message}")
                    result["checks"]["cors"]["warning"] = True

        # 4. API Endpoints (full check)
        if full_check and ("backend" in service_name or "api" in service_name):
            print(f"  🔌 API Endpoints:")
            endpoint_results = self.check_api_endpoints(url)

            for endpoint, (success, message) in endpoint_results.items():
                status_icon = "✅" if success else "❌"
                print(f"     {status_icon} {endpoint}: {message}")

            result["checks"]["endpoints"] = endpoint_results

        # Determine overall status
        critical_checks = ["http", "ssl"]
        critical_passed = all(
            result["checks"].get(check, {}).get("success", False)
            for check in critical_checks
            if check in result["checks"]
        )

        result["status"] = "pass" if critical_passed else "fail"

        return result

    def validate_all(self, full_check: bool = False) -> bool:
        """Validate all services for the environment."""
        print(f"\n{'='*60}")
        print(f"🚀 BRAIN Deployment Validation")
        print(f"Environment: {self.environment}")
        print(f"Timestamp: {self.results['timestamp']}")
        print(f"{'='*60}")

        config = DOMAIN_CONFIG.get(self.environment)
        if not config:
            print(f"❌ Invalid environment: {self.environment}")
            return False

        all_passed = True

        for service_name, url in config.items():
            service_result = self.validate_service(service_name, url, full_check)
            self.results["checks"][service_name] = service_result

            self.results["summary"]["total"] += 1

            if service_result["status"] == "pass":
                self.results["summary"]["passed"] += 1
            else:
                self.results["summary"]["failed"] += 1
                all_passed = False

            # Count warnings
            for check_name, check_data in service_result["checks"].items():
                if check_data.get("warning"):
                    self.results["summary"]["warnings"] += 1

        # Print summary
        print(f"\n{'='*60}")
        print("📊 VALIDATION SUMMARY")
        print(f"{'='*60}")
        print(f"Total Checks: {self.results['summary']['total']}")
        print(f"✅ Passed: {self.results['summary']['passed']}")
        print(f"❌ Failed: {self.results['summary']['failed']}")
        print(f"⚠️  Warnings: {self.results['summary']['warnings']}")

        if all_passed:
            print(f"\n✅ ALL CHECKS PASSED")
        else:
            print(f"\n❌ SOME CHECKS FAILED")
            print("   Review errors above and run troubleshooting")

        print(f"{'='*60}")

        return all_passed

    def save_report(self, output_file: str = None):
        """Save validation report to JSON."""
        if output_file is None:
            output_file = f"validation_report_{self.environment}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

        with open(output_file, "w") as f:
            json.dump(self.results, f, indent=2)

        print(f"\n💾 Report saved: {output_file}")


# ========================================
# QUICK CHECKS
# ========================================

def quick_check_all_envs():
    """Quick check all environments."""
    print("\n🔍 QUICK CHECK - All Environments\n")

    for env in ["dev", "stage", "prod"]:
        config = DOMAIN_CONFIG.get(env, {})
        print(f"\n{env.upper()}:")

        for service, url in config.items():
            try:
                response = requests.get(url, timeout=5, verify=True)
                status = "✅" if response.status_code == 200 else f"⚠️  {response.status_code}"
                print(f"  {status} {service}: {url}")
            except Exception as e:
                print(f"  ❌ {service}: {url} - {e}")


# ========================================
# MAIN CLI
# ========================================

def main():
    parser = argparse.ArgumentParser(
        description="BRAIN Deployment Validation Script",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic validation for DEV
  python3 validate_brain_deployment.py --env dev

  # Full validation with API endpoint checks
  python3 validate_brain_deployment.py --env prod --full

  # Quick check all environments
  python3 validate_brain_deployment.py --quick
        """
    )

    parser.add_argument(
        "--env",
        choices=["dev", "stage", "prod"],
        help="Environment to validate"
    )

    parser.add_argument(
        "--full",
        action="store_true",
        help="Full validation (includes all API endpoints)"
    )

    parser.add_argument(
        "--quick",
        action="store_true",
        help="Quick check all environments (basic HTTP only)"
    )

    parser.add_argument(
        "--timeout",
        type=int,
        default=10,
        help="Request timeout in seconds (default: 10)"
    )

    parser.add_argument(
        "--output",
        help="Output file for JSON report"
    )

    args = parser.parse_args()

    # Quick mode
    if args.quick:
        quick_check_all_envs()
        return

    # Normal mode requires --env
    if not args.env:
        print("❌ Error: --env required (or use --quick)")
        parser.print_help()
        sys.exit(1)

    # Run validation
    validator = BrainValidator(args.env, timeout=args.timeout)

    try:
        success = validator.validate_all(full_check=args.full)

        # Save report
        if args.output:
            validator.save_report(args.output)

        sys.exit(0 if success else 1)

    except KeyboardInterrupt:
        print("\n\n❌ Validation interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Validation failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
