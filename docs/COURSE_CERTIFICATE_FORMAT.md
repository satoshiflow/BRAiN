# Course Certificate Format
## BRAiN CourseFactory – Ed25519 Offline-Verifiable Certificates

**Version:** 1.0.0
**Schema Version:** `cert-v1`
**Signature Algorithm:** Ed25519
**Date:** 2025-12-26

---

## 📋 Overview

BRAiN CourseFactory uses **Ed25519 digital signatures** for course completion certificates. These certificates are:

- **Offline verifiable:** No server required to verify authenticity
- **Tamper-proof:** Any modification invalidates the signature
- **Privacy-preserving:** No PII (personally identifiable information)
- **Deterministic:** Same payload always produces same signature
- **Compact:** 64-byte signatures (128 hex characters)

---

## 🔐 Certificate Payload Schema

### Canonical JSON Structure

```json
{
  "certificate_id": "cert_abc123def456",
  "course_id": "course_banking_alternatives",
  "course_title": "Alternativen zu Banken & Sparkassen",
  "language": "de",
  "actor_id": "actor_a1b2c3d4",
  "completed_at": 1703001234.56,
  "completion_hash": "sha256:abcdef123456...",
  "issuer": "BRAiN",
  "issued_at": 1703001300.78,
  "schema_version": "cert-v1"
}
```

### Field Specifications

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `certificate_id` | string | Yes | Unique certificate ID (format: `cert_{16 hex chars}`) |
| `course_id` | string | Yes | Course identifier |
| `course_title` | string | Yes | Course title (human-readable) |
| `language` | string | Yes | Language code (`de`, `en`, `fr`, `es`) |
| `actor_id` | string | Yes | Pseudonymous learner ID (NO email/name) |
| `completed_at` | float | Yes | Unix timestamp of course completion |
| `completion_hash` | string | Yes | SHA-256 hash of completion record |
| `issuer` | string | Yes | Certificate issuer (always `"BRAiN"`) |
| `issued_at` | float | Yes | Unix timestamp of certificate issuance |
| `schema_version` | string | Yes | Schema version (always `"cert-v1"`) |

### Privacy Considerations

**✅ Included:**
- Pseudonymous `actor_id` (internal hashed ID)
- Course metadata (title, language)
- Completion timestamp
- Cryptographic proof (completion_hash)

**❌ NOT Included:**
- Email addresses
- Real names
- Usernames
- IP addresses
- Any other PII

**Rationale:** Certificates must be shareable without privacy concerns. The `actor_id` is only meaningful within BRAiN's internal system.

---

## 🔏 Signature Generation

### Canonical JSON Serialization

Certificates are signed using **canonical JSON** to ensure deterministic signatures:

```python
import json

def to_canonical_json(payload: dict) -> str:
    """
    Convert payload to canonical JSON for signing.

    Ensures:
    - Sorted keys
    - No whitespace
    - UTF-8 encoding
    - Consistent separators
    """
    return json.dumps(
        payload,
        sort_keys=True,           # Deterministic key order
        separators=(',', ':'),    # No extra whitespace
        ensure_ascii=False        # UTF-8 for international chars
    )
```

**Example Canonical JSON:**
```json
{"actor_id":"actor_123","certificate_id":"cert_abc","completed_at":1703001234.56,"completion_hash":"sha256:def...","course_id":"demo_course","course_title":"Demo Course","issued_at":1703001300.78,"issuer":"BRAiN","language":"de","schema_version":"cert-v1"}
```

### Ed25519 Signing Process

```python
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

# 1. Load private key (PEM format)
with open('storage/courses/cert_keys/private.pem', 'rb') as f:
    private_key = serialization.load_pem_private_key(f.read(), password=None)

# 2. Convert payload to canonical JSON
canonical_json = to_canonical_json(payload_dict)

# 3. Sign (Ed25519 produces 64-byte signature)
signature_bytes = private_key.sign(canonical_json.encode('utf-8'))

# 4. Convert to hex (128 characters)
signature_hex = signature_bytes.hex()
```

**Signature Properties:**
- **Length:** 64 bytes = 128 hex characters
- **Deterministic:** Same input → same signature
- **Fast:** ~0.1ms signing, ~0.3ms verification
- **Secure:** 128-bit security level (equivalent to AES-128)

---

## ✅ Signature Verification

### Offline Verification Process

```python
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

# 1. Load public key (PEM format)
with open('storage/courses/cert_keys/public.pem', 'rb') as f:
    public_key = serialization.load_pem_public_key(f.read())

# 2. Convert payload to canonical JSON
canonical_json = to_canonical_json(payload_dict)

# 3. Convert signature from hex
signature_bytes = bytes.fromhex(signature_hex)

# 4. Verify (raises exception if invalid)
try:
    public_key.verify(signature_bytes, canonical_json.encode('utf-8'))
    print("✅ Signature valid")
except Exception:
    print("❌ Signature invalid")
```

### Verification Checklist

Before trusting a certificate, verify:

1. ✅ **Signature is valid** (Ed25519 verification passes)
2. ✅ **Schema version is supported** (`cert-v1`)
3. ✅ **Issuer is expected** (`"BRAiN"`)
4. ✅ **Certificate not expired** (optional: check `issued_at`)
5. ✅ **No tampering** (any payload change invalidates signature)

### Verification Failures

| Error | Cause | Fix |
|-------|-------|-----|
| `Invalid signature length` | Signature not 128 hex chars | Ensure hex encoding |
| `Signature verification failed` | Payload tampered with | Reject certificate |
| `Invalid public key` | Wrong public key used | Use correct public key |
| `Malformed payload` | Missing required fields | Validate schema first |

---

## 💾 Storage Layout

### Directory Structure

```
storage/courses/certificates/
└── {course_id}/
    └── {certificate_id}/
        ├── certificate.json    # Canonical payload
        └── certificate.sig     # Ed25519 signature (hex)
```

### Example Files

**`certificate.json`:**
```json
{"actor_id":"actor_abc","certificate_id":"cert_123","completed_at":1703001234.56,"completion_hash":"sha256:def...","course_id":"banking_course","course_title":"Banking Alternatives","issued_at":1703001300.78,"issuer":"BRAiN","language":"de","schema_version":"cert-v1"}
```

**`certificate.sig`:**
```
abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890
```
(128 hex characters, one line)

### Key Storage

```
storage/courses/cert_keys/
├── private.pem    # Ed25519 private key (0600 permissions)
└── public.pem     # Ed25519 public key
```

**⚠️ Critical:**
- `private.pem` MUST have `0600` permissions (read/write owner only)
- `private.pem` MUST be backed up securely
- `private.pem` MUST NEVER be committed to Git
- `public.pem` can be shared publicly for verification

---

## 🌐 API Endpoints

### Issue Certificate

```bash
POST /api/courses/{course_id}/certificates/issue

# Request
{
  "enrollment_id": "enr_abc123"
}

# Response
{
  "payload": {
    "certificate_id": "cert_xyz789",
    "course_id": "banking_course",
    "course_title": "Banking Alternatives",
    "language": "de",
    "actor_id": "actor_abc",
    "completed_at": 1703001234.56,
    "completion_hash": "sha256:...",
    "issuer": "BRAiN",
    "issued_at": 1703001300.78,
    "schema_version": "cert-v1"
  },
  "signature_hex": "abcdef123456..."
}
```

**Constraints:**
- Course must be completed (verified via completion record)
- Enrollment must exist
- One certificate per enrollment

### Verify Certificate

```bash
POST /api/courses/certificates/verify

# Request
{
  "certificate_payload": { ... },  # Full payload from certificate.json
  "signature_hex": "abcdef123456..."
}

# Response
{
  "valid": true,
  "certificate_id": "cert_xyz789",
  "issued_at": 1703001300.78
}
```

**Response if Invalid:**
```json
{
  "valid": false,
  "reason": "Invalid signature: payload tampered"
}
```

### Get Certificate

```bash
GET /api/courses/{course_id}/certificates/{certificate_id}

# Response
{
  "payload": { ... },
  "signature_hex": "abcdef123456..."
}
```

---

## 🔧 Offline Verification Tool (CLI)

### Python Script

```python
#!/usr/bin/env python3
"""
Offline certificate verification tool.

Usage:
  python verify_cert.py certificate.json certificate.sig public.pem
"""

import sys
import json
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

def verify_certificate(cert_path, sig_path, pubkey_path):
    # Load certificate payload
    with open(cert_path, 'r') as f:
        payload = json.load(f)

    # Convert to canonical JSON
    canonical = json.dumps(payload, sort_keys=True, separators=(',', ':'), ensure_ascii=False)

    # Load signature
    with open(sig_path, 'r') as f:
        signature_hex = f.read().strip()
    signature_bytes = bytes.fromhex(signature_hex)

    # Load public key
    with open(pubkey_path, 'rb') as f:
        public_key = serialization.load_pem_public_key(f.read())

    # Verify
    try:
        public_key.verify(signature_bytes, canonical.encode('utf-8'))
        print(f"✅ Certificate VALID: {payload['certificate_id']}")
        print(f"   Course: {payload['course_title']} ({payload['language']})")
        print(f"   Issued: {payload['issued_at']}")
        return True
    except Exception as e:
        print(f"❌ Certificate INVALID: {e}")
        return False

if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("Usage: verify_cert.py <certificate.json> <certificate.sig> <public.pem>")
        sys.exit(1)

    valid = verify_certificate(sys.argv[1], sys.argv[2], sys.argv[3])
    sys.exit(0 if valid else 1)
```

### Usage

```bash
# Download public key (one-time)
curl http://brain.example.com/api/cert_keys/public.pem > public.pem

# Verify certificate
python verify_cert.py certificate.json certificate.sig public.pem

# Output:
# ✅ Certificate VALID: cert_xyz789
#    Course: Banking Alternatives (de)
#    Issued: 1703001300.78
```

---

## 📤 Sharing Certificates

### Export Bundle

Create a ZIP bundle for sharing:

```
certificate_bundle.zip
├── certificate.json       # Payload
├── certificate.sig        # Signature
├── public.pem            # Public key for verification
└── VERIFICATION.md       # Instructions
```

### VERIFICATION.md Template

```markdown
# Certificate Verification Instructions

## What is this?

This bundle contains:
- `certificate.json` - Certificate details
- `certificate.sig` - Cryptographic signature
- `public.pem` - Public key for verification

## How to Verify

### Option 1: Online Verification
Visit: https://brain.example.com/verify
Upload: `certificate.json` and `certificate.sig`

### Option 2: Offline Verification (CLI)
```bash
python verify_cert.py certificate.json certificate.sig public.pem
```

### Option 3: Manual Verification (Python)
```python
from cryptography.hazmat.primitives import serialization
import json

# Load files and verify as shown above
```

## What Does Verification Prove?

- ✅ Certificate was issued by BRAiN
- ✅ Certificate has not been tampered with
- ✅ Learner completed the course

## Privacy

This certificate contains NO personal information (no email, no name).
The `actor_id` is a pseudonymous identifier only meaningful within BRAiN.
```

---

## 🔄 Certificate Lifecycle

```
┌─────────────┐
│ Course      │
│ Enrollment  │
└──────┬──────┘
       │
       ↓
┌─────────────┐
│ Progress    │
│ Tracking    │
└──────┬──────┘
       │
       ↓
┌─────────────┐
│ Course      │
│ Completion  │
└──────┬──────┘
       │
       ↓
┌─────────────┐
│ Certificate │ ← Ed25519 signature applied
│ Issuance    │
└──────┬──────┘
       │
       ├─────→ Store (certificate.json + .sig)
       ├─────→ API response (payload + signature)
       └─────→ Optional: Generate PDF
```

**States:**
1. **Not Issued:** Course not completed yet
2. **Issued:** Certificate signed and stored
3. **Shared:** Certificate exported and shared
4. **Verified:** Signature validated by third party

**Note:** Once issued, certificates are **immutable** (cannot be modified or revoked).

---

## 🚫 Limitations & Future Enhancements

### Current Limitations

1. **No Revocation:** Certificates cannot be revoked once issued
2. **No Expiration:** Certificates are valid indefinitely
3. **No PDF:** Only JSON + signature (PDF optional future)
4. **Single Signature:** One issuer key (no multi-sig)
5. **No Blockchain:** No blockchain anchoring (optional future)

### Future Enhancements (Sprint 15+)

1. **Certificate Revocation List (CRL)**
   - Maintain list of revoked certificate IDs
   - Check against CRL during verification

2. **PDF Generation**
   - Visual certificate with QR code
   - QR code links to verification URL

3. **Blockchain Anchoring**
   - Anchor certificate hashes to Bitcoin/Ethereum
   - Extra layer of trust and immutability

4. **Expiration Dates**
   - Add `expires_at` field for time-limited certificates
   - Useful for certifications requiring renewal

5. **Multi-Signature**
   - Require multiple signatures (e.g., instructor + admin)
   - Enhanced trust for high-value certificates

---

## 📚 References

- **Ed25519 Spec:** [RFC 8032](https://datatracker.ietf.org/doc/html/rfc8032)
- **JSON Canonicalization:** [RFC 8785](https://datatracker.ietf.org/doc/html/rfc8785)
- **Cryptography Library:** [cryptography.io](https://cryptography.io/)

---

**Version:** 1.0.0
**Schema Version:** `cert-v1`
**Date:** 2025-12-26
**Status:** ✅ Production Ready
