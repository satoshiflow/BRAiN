# PayCore Module

**Version:** 1.0.0
**Status:** ✅ Production Ready
**Location:** `backend/app/modules/paycore/`

---

## Overview

**PayCore** is BRAiN's centralized payment processing infrastructure, providing:

- **Multi-Provider Support** - Stripe (production-ready), PayPal (stub), Crypto (planned)
- **Provider-Agnostic API** - Adapter pattern for consistent interface across providers
- **Append-Only Ledger** - Immutable transaction records for auditability
- **Event-Driven Architecture** - Redis Streams for real-time payment events
- **Policy-Based Refunds** - High-value refunds require policy approval
- **Webhook Idempotency** - Duplicate webhook events are automatically ignored
- **Secure Webhook Verification** - Signature verification for all webhooks

---

## Architecture

```
PayCore Module
├── Models (models.py)
│   ├── PaymentIntent - Checkout sessions
│   ├── Transaction - Append-only ledger
│   ├── Refund - Refund records
│   └── RevenueDaily - Aggregation table (optional)
│
├── Schemas (schemas.py)
│   ├── IntentCreateRequest/Response
│   ├── RefundCreateRequest/Response
│   ├── TransactionRecord
│   └── Provider schemas (ProviderIntent, ProviderRefund)
│
├── Providers (providers/)
│   ├── base.py - PaymentProvider interface
│   ├── stripe.py - Stripe implementation
│   └── paypal.py - PayPal stub (TODO)
│
├── Service (service.py)
│   ├── Intent management
│   ├── Refund processing
│   ├── Webhook handling
│   └── Event publishing
│
└── API (router.py)
    ├── POST /api/paycore/intents - Create payment
    ├── GET /api/paycore/intents/{id} - Get status
    ├── POST /api/paycore/refunds - Request refund
    ├── POST /api/paycore/webhooks/stripe - Stripe webhook
    └── POST /api/paycore/webhooks/paypal - PayPal webhook (stub)
```

---

## Setup

### 1. Environment Variables

Add to your `.env` file:

```bash
# Stripe Configuration
STRIPE_SECRET_KEY=sk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...
STRIPE_SUCCESS_URL=https://yourdomain.com/payment/success
STRIPE_CANCEL_URL=https://yourdomain.com/payment/cancel

# PayCore Settings
PAYCORE_DEFAULT_CURRENCY=EUR
PAYCORE_REFUND_SUPERVISOR_THRESHOLD=10000
```

**Get Stripe Keys:**
1. Sign up at https://stripe.com
2. Go to https://dashboard.stripe.com/apikeys
3. Copy "Secret key" → `STRIPE_SECRET_KEY`
4. Get webhook secret (see Webhook Setup below)

### 2. Database Migration

Run Alembic migration to create PayCore tables:

```bash
cd backend
alembic upgrade head
```

This creates:
- `paycore_intents`
- `paycore_transactions`
- `paycore_refunds`
- `paycore_revenue_daily`

### 3. Install Stripe SDK

```bash
pip install stripe
```

Or add to `requirements.txt`:
```
stripe>=5.0.0
```

---

## Webhook Setup

### Stripe Webhooks

**Local Development (using Stripe CLI):**

1. Install Stripe CLI: https://stripe.com/docs/stripe-cli
2. Login: `stripe login`
3. Forward webhooks to local server:
   ```bash
   stripe listen --forward-to localhost:8000/api/paycore/webhooks/stripe
   ```
4. Copy the webhook signing secret (starts with `whsec_`) to `.env`:
   ```bash
   STRIPE_WEBHOOK_SECRET=whsec_...
   ```

**Production (Stripe Dashboard):**

1. Go to https://dashboard.stripe.com/webhooks
2. Click "Add endpoint"
3. Enter your webhook URL: `https://yourdomain.com/api/paycore/webhooks/stripe`
4. Select events to listen for:
   - `checkout.session.completed`
   - `checkout.session.expired`
   - `charge.refunded`
5. Copy the signing secret to your `.env`

---

## Usage

### 1. Create Payment Intent

**Request:**
```bash
curl -X POST http://localhost:8000/api/paycore/intents \
  -H "Content-Type: application/json" \
  -d '{
    "amount_cents": 5000,
    "currency": "EUR",
    "provider": "stripe",
    "user_id": "user_123",
    "metadata": {
      "course_id": "course_abc",
      "product_type": "course_purchase"
    }
  }'
```

**Response:**
```json
{
  "intent_id": "550e8400-e29b-41d4-a716-446655440000",
  "provider": "stripe",
  "provider_intent_id": "cs_test_a1b2c3...",
  "status": "created",
  "amount_cents": 5000,
  "currency": "EUR",
  "checkout_url": "https://checkout.stripe.com/c/pay/cs_test_a1b2c3...",
  "created_at": "2025-12-27T10:00:00Z"
}
```

**Next Step:** Redirect user to `checkout_url` to complete payment.

### 2. Check Payment Status

**Request:**
```bash
curl http://localhost:8000/api/paycore/intents/550e8400-e29b-41d4-a716-446655440000
```

**Response:**
```json
{
  "intent_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "succeeded",
  "amount_cents": 5000,
  "currency": "EUR",
  "provider": "stripe",
  "metadata": {
    "course_id": "course_abc"
  },
  "created_at": "2025-12-27T10:00:00Z",
  "updated_at": "2025-12-27T10:05:00Z"
}
```

### 3. Request Refund

**Request:**
```bash
curl -X POST http://localhost:8000/api/paycore/refunds \
  -H "Content-Type: application/json" \
  -d '{
    "intent_id": "550e8400-e29b-41d4-a716-446655440000",
    "amount_cents": 5000,
    "reason": "Customer requested refund"
  }'
```

**Response:**
```json
{
  "refund_id": "660e8400-e29b-41d4-a716-446655440000",
  "intent_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "processing",
  "amount_cents": 5000,
  "reason": "Customer requested refund",
  "requested_by": "user_admin",
  "created_at": "2025-12-27T11:00:00Z"
}
```

**Note:** Refunds above `PAYCORE_REFUND_SUPERVISOR_THRESHOLD` are checked against Policy Engine.

---

## Integration with Other Modules

### Course Factory Integration

**Example: Purchase Course**

```python
from app.modules.paycore.service import get_paycore_service
from app.modules.paycore.schemas import IntentCreateRequest

# Create payment for course purchase
paycore = get_paycore_service()

intent_request = IntentCreateRequest(
    amount_cents=5000,  # 50.00 EUR
    currency="EUR",
    provider="stripe",
    user_id=user_id,
    metadata={
        "course_id": course_id,
        "product_type": "course_purchase",
        "tenant_id": tenant_id,
    }
)

intent_response = await paycore.create_intent(intent_request, tenant_id)

# Redirect user to intent_response.checkout_url
return {"checkout_url": intent_response.checkout_url}
```

**Listen for Payment Events:**

```python
from app.core.redis_client import get_redis
import json

redis = await get_redis()

# Subscribe to PayCore events
while True:
    events = redis.xread({"brain.events.paycore": "0"}, count=10)

    for stream, messages in events:
        for message_id, data in messages:
            event = json.loads(data[b"data"])

            if event["event_type"] == "payment_succeeded":
                # Grant course access
                await grant_course_access(
                    user_id=event["metadata"]["user_id"],
                    course_id=event["metadata"]["course_id"]
                )
```

---

## Event Contracts

PayCore publishes events to Redis Stream: `brain.events.paycore`

### Event Types

#### 1. `intent_created`
```json
{
  "event_type": "intent_created",
  "intent_id": "uuid",
  "tenant_id": "tenant_001",
  "amount_cents": 5000,
  "currency": "EUR",
  "provider": "stripe",
  "metadata": {"course_id": "course_123"},
  "timestamp": 1703001234.56
}
```

#### 2. `payment_succeeded`
```json
{
  "event_type": "payment_succeeded",
  "transaction_id": "uuid",
  "intent_id": "uuid",
  "amount_cents": 5000,
  "provider": "stripe",
  "timestamp": 1703001234.56
}
```

#### 3. `payment_failed`
```json
{
  "event_type": "payment_failed",
  "intent_id": "uuid",
  "provider": "stripe",
  "timestamp": 1703001234.56
}
```

#### 4. `refund_requested`
```json
{
  "event_type": "refund_requested",
  "refund_id": "uuid",
  "intent_id": "uuid",
  "amount_cents": 5000,
  "requested_by": "user_admin",
  "timestamp": 1703001234.56
}
```

---

## Testing

### Unit Tests (TODO)

```bash
pytest backend/app/modules/paycore/tests/
```

### Webhook Testing with Stripe CLI

**Trigger Test Webhook:**
```bash
stripe trigger checkout.session.completed
```

**View Logs:**
```bash
docker compose logs -f backend | grep paycore
```

**Expected Log:**
```
[PayCore] Webhook received: payment_succeeded (event_id=evt_...)
[PayCore] Transaction recorded: uuid
[PayCore] Published event: payment_succeeded
```

---

## Security

### Webhook Signature Verification

All webhooks are verified using provider-specific signatures:

- **Stripe:** `stripe.Webhook.construct_event()` with `STRIPE_WEBHOOK_SECRET`
- **PayPal:** TODO - implement PayPal webhook verification

**Failed Verification → 400 Bad Request**

### Idempotency

Duplicate webhook events are automatically detected using `provider_event_id`:

```sql
SELECT * FROM paycore_transactions
WHERE provider_event_id = 'evt_123'
```

If found → Return `{"processed": false}` without processing.

### Refund Policy Checks

High-value refunds trigger Policy Engine evaluation:

```python
if amount_cents > PAYCORE_REFUND_SUPERVISOR_THRESHOLD:
    policy_result = await policy_engine.evaluate({
        "agent_id": principal.principal_id,
        "action": "paycore.refund",
        "resource": intent_id,
        "params": {"amount_cents": amount_cents}
    })

    if not policy_result.allowed:
        raise RefundDeniedException(policy_result.reason)
```

---

## API Reference

### Endpoints

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| GET | `/api/paycore/info` | Module information | No |
| GET | `/api/paycore/health` | Health check | No |
| POST | `/api/paycore/intents` | Create payment intent | Yes |
| GET | `/api/paycore/intents/{id}` | Get intent status | No |
| GET | `/api/paycore/intents/{id}/status` | Simple status check | No |
| POST | `/api/paycore/refunds` | Request refund | Yes |
| GET | `/api/paycore/refunds/{id}` | Get refund status | No |
| POST | `/api/paycore/webhooks/stripe` | Stripe webhook | No |
| POST | `/api/paycore/webhooks/paypal` | PayPal webhook (stub) | No |

---

## Database Schema

### `paycore_intents`

| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| tenant_id | String(100) | Tenant ID (indexed) |
| user_id | String(100) | User ID (nullable) |
| provider | Enum | stripe/paypal/crypto |
| provider_intent_id | String(255) | Provider's intent ID (unique) |
| amount_cents | Integer | Amount in cents |
| currency | String(3) | ISO currency code |
| status | Enum | created/pending/succeeded/failed/cancelled |
| metadata | JSONB | Custom metadata |
| created_at | DateTime | Creation timestamp |
| updated_at | DateTime | Last update timestamp |

### `paycore_transactions` (Ledger)

| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| intent_id | UUID | FK to paycore_intents |
| event_type | Enum | payment_succeeded/failed/refund_succeeded/etc. |
| provider_event_id | String(255) | Idempotency key (unique) |
| amount_cents | Integer | Amount in cents |
| currency | String(3) | ISO currency code |
| provider_data | JSONB | Raw webhook data |
| created_at | DateTime | Creation timestamp (append-only) |

### `paycore_refunds`

| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| intent_id | UUID | FK to paycore_intents |
| transaction_id | UUID | FK to paycore_transactions |
| amount_cents | Integer | Refund amount in cents |
| reason | String(500) | Refund reason |
| status | Enum | requested/processing/succeeded/failed |
| requested_by | String(100) | User who requested |
| approved_by | String(100) | User who approved (nullable) |
| provider_refund_id | String(255) | Provider's refund ID |
| created_at | DateTime | Creation timestamp |
| updated_at | DateTime | Last update timestamp |

---

## Troubleshooting

### Webhook Not Received

1. **Check Stripe CLI is running:**
   ```bash
   stripe listen --forward-to localhost:8000/api/paycore/webhooks/stripe
   ```

2. **Verify webhook secret in .env:**
   ```bash
   echo $STRIPE_WEBHOOK_SECRET
   ```

3. **Check backend logs:**
   ```bash
   docker compose logs -f backend | grep webhook
   ```

### Payment Status Not Updating

1. **Check transaction ledger:**
   ```sql
   SELECT * FROM paycore_transactions WHERE intent_id = 'your-uuid';
   ```

2. **Verify webhook was processed:**
   ```bash
   # Should see: "Webhook received: payment_succeeded"
   docker compose logs backend | grep "Webhook received"
   ```

3. **Check for idempotency issues:**
   ```sql
   SELECT provider_event_id, COUNT(*)
   FROM paycore_transactions
   GROUP BY provider_event_id
   HAVING COUNT(*) > 1;
   ```

### Refund Policy Denied

If refund fails with "Refund denied by policy":

1. **Check threshold:**
   ```bash
   echo $PAYCORE_REFUND_SUPERVISOR_THRESHOLD
   ```

2. **View policy rules:**
   ```bash
   curl http://localhost:8000/api/policy/policies
   ```

3. **Lower threshold or update policy:**
   ```bash
   # In .env
   PAYCORE_REFUND_SUPERVISOR_THRESHOLD=50000  # 500.00 EUR
   ```

---

## Roadmap

### Phase 1 (MVP) ✅
- [x] Stripe integration
- [x] Payment intent creation
- [x] Webhook handling with idempotency
- [x] Refund processing
- [x] Event publishing
- [x] Policy integration for refunds

### Phase 2 (Q1 2025)
- [ ] PayPal integration
- [ ] Subscription support (recurring payments)
- [ ] Revenue analytics dashboard
- [ ] Daily aggregation worker
- [ ] Multi-currency support

### Phase 3 (Q2 2025)
- [ ] Crypto payments (Bitcoin, Ethereum)
- [ ] Invoice generation
- [ ] Tax calculation integration
- [ ] Payout management
- [ ] Fraud detection hooks

---

## Support

**Module Owner:** BRAiN Core Team
**Documentation:** This README
**API Docs:** http://localhost:8000/docs (FastAPI auto-generated)

For issues or questions, see:
- Stripe Docs: https://stripe.com/docs
- BRAiN CLAUDE.md: `/CLAUDE.md`
