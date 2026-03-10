#!/usr/bin/env python3
"""
BRAiN Runtime Preflight Validator

Validates runtime configuration before startup/deploy to prevent common misconfigurations.
Blocks production deploys with localhost URLs, missing secrets, or insecure CORS.

Usage:
    python3 scripts/preflight_runtime.py [--strict]
    
Exit codes:
    0 = All validations passed
    1 = Validation failed (critical error)
    2 = Warnings only (non-critical)
"""

import os
import sys
from typing import List, Tuple
from urllib.parse import urlparse


class ValidationError:
    """Validation error with severity."""
    def __init__(self, severity: str, message: str):
        self.severity = severity  # "error" or "warning"
        self.message = message


def detect_runtime_mode() -> str:
    """Detect runtime mode using same logic as backend/app/core/config.py"""
    explicit = os.getenv("BRAIN_RUNTIME_MODE", "auto").lower()
    if explicit in ["local", "remote"]:
        return explicit
    
    # Auto-detection
    if os.getenv("SERVICE_FQDN_BACKEND") or os.getenv("COOLIFY_APP_ID"):
        return "remote"
    
    if os.path.exists("/.dockerenv"):
        if os.getenv("COOLIFY_APP_ID"):
            return "remote"
        return "local"
    
    return "remote"  # Default: fail-safe


def is_localhost_url(url: str) -> bool:
    """Check if URL points to localhost."""
    if not url:
        return False
    
    localhost_indicators = ["localhost", "127.0.0.1", "::1", "0.0.0.0"]
    
    try:
        parsed = urlparse(url)
        hostname = parsed.hostname or ""
        return any(indicator in hostname.lower() for indicator in localhost_indicators)
    except Exception:
        return False


def validate_backend_config(mode: str) -> List[ValidationError]:
    """Validate backend configuration."""
    errors = []
    
    # Database URL
    database_url = os.getenv("DATABASE_URL", "")
    if mode == "remote":
        if not database_url:
            errors.append(ValidationError("error", "Remote mode: DATABASE_URL is required"))
        elif is_localhost_url(database_url):
            errors.append(ValidationError("error", f"Remote mode: DATABASE_URL cannot point to localhost: {database_url}"))
    
    # Redis URL
    redis_url = os.getenv("REDIS_URL", "")
    if mode == "remote":
        if not redis_url:
            errors.append(ValidationError("error", "Remote mode: REDIS_URL is required"))
        elif is_localhost_url(redis_url):
            errors.append(ValidationError("error", f"Remote mode: REDIS_URL cannot point to localhost: {redis_url}"))
    
    # CORS Origins
    cors_origins = os.getenv("CORS_ORIGINS", "")
    if cors_origins:
        if "*" in cors_origins:
            if mode == "remote":
                errors.append(ValidationError("error", "Remote mode: CORS wildcard '*' is not allowed"))
            else:
                errors.append(ValidationError("warning", "Local mode: CORS wildcard '*' detected (acceptable for dev)"))
        
        # Check for localhost in remote CORS
        if mode == "remote" and is_localhost_url(cors_origins):
            errors.append(ValidationError("error", f"Remote mode: CORS_ORIGINS contains localhost: {cors_origins}"))
    
    # JWT/Security secrets (remote only)
    if mode == "remote":
        jwt_secret = os.getenv("JWT_SECRET_KEY", "")
        if not jwt_secret:
            errors.append(ValidationError("warning", "Remote mode: JWT_SECRET_KEY not set (may be required)"))
        
        dmz_secret = os.getenv("BRAIN_DMZ_GATEWAY_SECRET", "")
        if not dmz_secret:
            errors.append(ValidationError("warning", "Remote mode: BRAIN_DMZ_GATEWAY_SECRET not set (may be required)"))
    
    return errors


def validate_frontend_config(mode: str) -> List[ValidationError]:
    """Validate frontend configuration."""
    errors = []
    
    # API Base URL
    api_base = os.getenv("NEXT_PUBLIC_BRAIN_API_BASE", "")
    if api_base:
        if mode == "remote" and is_localhost_url(api_base):
            errors.append(ValidationError("error", f"Remote mode: NEXT_PUBLIC_BRAIN_API_BASE cannot point to localhost: {api_base}"))
    
    # App Environment
    app_env = os.getenv("NEXT_PUBLIC_APP_ENV", "")
    if app_env == "local" and mode == "remote":
        errors.append(ValidationError("warning", "NEXT_PUBLIC_APP_ENV=local but runtime detected as remote"))
    
    return errors


def validate_node_env() -> List[ValidationError]:
    """Validate NODE_ENV consistency."""
    errors = []
    node_env = os.getenv("NODE_ENV", "development")
    
    if node_env == "production":
        # Check for development artifacts in production
        api_base = os.getenv("NEXT_PUBLIC_BRAIN_API_BASE", "")
        if is_localhost_url(api_base):
            errors.append(ValidationError("error", f"NODE_ENV=production but API points to localhost: {api_base}"))
    
    return errors


def main():
    """Run all preflight validations."""
    strict_mode = "--strict" in sys.argv
    
    print("🔍 BRAiN Runtime Preflight Validator")
    print("=" * 50)
    
    # Detect runtime mode
    mode = detect_runtime_mode()
    print(f"Runtime Mode: {mode}")
    
    explicit_mode = os.getenv("BRAIN_RUNTIME_MODE", "auto")
    if explicit_mode != "auto":
        print(f"  (explicitly set: BRAIN_RUNTIME_MODE={explicit_mode})")
    else:
        print(f"  (auto-detected)")
    
    print()
    
    # Run validations
    all_errors: List[ValidationError] = []
    
    print("📋 Backend Configuration...")
    backend_errors = validate_backend_config(mode)
    all_errors.extend(backend_errors)
    
    print("📋 Frontend Configuration...")
    frontend_errors = validate_frontend_config(mode)
    all_errors.extend(frontend_errors)
    
    print("📋 Node Environment...")
    node_errors = validate_node_env()
    all_errors.extend(node_errors)
    
    # Report results
    print()
    print("=" * 50)
    
    errors = [e for e in all_errors if e.severity == "error"]
    warnings = [e for e in all_errors if e.severity == "warning"]
    
    if errors:
        print(f"❌ FAILED: {len(errors)} error(s) found")
        print()
        for error in errors:
            print(f"  ❌ {error.message}")
        
        if warnings:
            print()
            print(f"⚠️  {len(warnings)} warning(s):")
            for warning in warnings:
                print(f"  ⚠️  {warning.message}")
        
        print()
        print("Preflight check FAILED. Fix errors before deployment.")
        sys.exit(1)
    
    elif warnings:
        print(f"⚠️  PASSED with warnings: {len(warnings)} warning(s)")
        print()
        for warning in warnings:
            print(f"  ⚠️  {warning.message}")
        
        if strict_mode:
            print()
            print("Preflight check FAILED (strict mode: warnings treated as errors)")
            sys.exit(1)
        else:
            print()
            print("Preflight check PASSED (warnings only)")
            sys.exit(2)
    
    else:
        print("✅ PASSED: All validations successful")
        print()
        print("Runtime configuration is valid for deployment.")
        sys.exit(0)


if __name__ == "__main__":
    main()
