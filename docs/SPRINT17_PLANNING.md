# Sprint 17 Planning Document
## Notification System & RBAC Enhancement

**Sprint:** 17
**Date:** 2025-12-27
**Status:** 🎯 Planning
**Branch:** `claude/sprint17-notifications-rbac-<session-id>`
**Build On:** Sprint 16 - HITL Approvals UI & Governance Cockpit

---

## Executive Summary

Sprint 17 focuses on **enterprise-grade enhancements** to the governance system delivered in Sprint 16. We will implement two critical missing pieces that transform BRAiN from a functional governance platform into an **enterprise-ready system**:

1. **Notification System** - Real-time alerts for governance events
2. **RBAC (Role-Based Access Control)** - Fine-grained permission management

### Strategic Goals

- 🔔 **Proactive Alerts** - Notify stakeholders instantly when approvals are needed
- 🔐 **Security Hardening** - Proper role-based access control
- 📧 **Multi-Channel Notifications** - Email, Webhook, Slack integration
- 👥 **Team Collaboration** - Support multiple actors with different permissions
- 🎯 **Reduced Approval Bottlenecks** - Faster response times via notifications

---

## Sprint Objectives

### Primary Deliverables

#### 1. Notification System (Phase 1)
**Goal:** Real-time notifications for governance events

**Features:**
- ✅ Email notifications for new approval requests
- ✅ Webhook support for external integrations
- ✅ Slack/Discord integration
- ✅ Notification preferences per user
- ✅ Notification templates (customizable)
- ✅ Retry logic for failed notifications
- ✅ Notification audit trail

**Notification Events:**
- Approval requested (PENDING)
- Approval approved (APPROVED)
- Approval rejected (REJECTED)
- Approval expiring soon (24h before expiry)
- Approval expired (EXPIRED)
- High/Critical risk approvals (immediate alert)

#### 2. RBAC System (Phase 2)
**Goal:** Fine-grained role-based access control

**Features:**
- ✅ Role definitions (Admin, Approver, Auditor, Viewer)
- ✅ Permission system (approve_ir, approve_course, view_audit, etc.)
- ✅ Role assignment API
- ✅ Permission checks in all governance endpoints
- ✅ Multi-level approval workflows (requires N approvers)
- ✅ Role hierarchy (Admin > Approver > Auditor > Viewer)
- ✅ RBAC audit trail

**Roles:**

| Role | Permissions | Description |
|------|-------------|-------------|
| **Admin** | All permissions | Full system access |
| **Approver** | Approve/reject approvals | Can make decisions |
| **Auditor** | View audit trail, export | Read-only compliance access |
| **Viewer** | View approvals (no actions) | Read-only observer |

**Permissions:**
- `approve_ir_escalation` - Approve IR escalations
- `approve_course_publish` - Approve course publishing
- `approve_certificate_issuance` - Approve certificates
- `approve_policy_override` - Approve policy overrides
- `view_audit` - View audit trail
- `export_audit` - Export audit logs
- `manage_roles` - Assign roles to users
- `view_stats` - View governance statistics

---

## Architecture Design

### Notification System Architecture

```
┌─────────────────────────────────────────────────────────┐
│              Notification System                         │
├─────────────────────────────────────────────────────────┤
│                                                           │
│  ┌──────────────┐    ┌──────────────┐    ┌───────────┐ │
│  │  Governance  │───▶│ Notification │───▶│  Channels │ │
│  │   Service    │    │   Manager    │    │           │ │
│  └──────────────┘    └──────────────┘    └───────────┘ │
│         │                    │                    │      │
│         │                    │                    │      │
│         ▼                    ▼                    ▼      │
│  ┌──────────────┐    ┌──────────────┐    ┌───────────┐ │
│  │   Events     │    │  Templates   │    │  Delivery │ │
│  │   Queue      │    │   Engine     │    │   Queue   │ │
│  └──────────────┘    └──────────────┘    └───────────┘ │
│                                                           │
└─────────────────────────────────────────────────────────┘
                           │
                           ▼
            ┌──────────────────────────────┐
            │   Notification Channels       │
            ├──────────────────────────────┤
            │ • Email (SMTP)                │
            │ • Webhook (HTTP POST)         │
            │ • Slack (Incoming Webhook)    │
            │ • Discord (Webhook)           │
            └──────────────────────────────┘
```

### RBAC System Architecture

```
┌─────────────────────────────────────────────────────────┐
│               RBAC System                                 │
├─────────────────────────────────────────────────────────┤
│                                                           │
│  ┌──────────────┐    ┌──────────────┐    ┌───────────┐ │
│  │    Actor     │───▶│     Role     │───▶│Permission │ │
│  │   (User)     │    │  Assignment  │    │   Check   │ │
│  └──────────────┘    └──────────────┘    └───────────┘ │
│         │                    │                    │      │
│         │                    │                    │      │
│         ▼                    ▼                    ▼      │
│  ┌──────────────┐    ┌──────────────┐    ┌───────────┐ │
│  │    Roles     │    │ Permissions  │    │   Audit   │ │
│  │  Registry    │    │  Registry    │    │   Trail   │ │
│  └──────────────┘    └──────────────┘    └───────────┘ │
│                                                           │
└─────────────────────────────────────────────────────────┘
```

---

## Implementation Plan

### Phase 1: Notification System (Days 1-3)

#### Day 1: Core Notification Infrastructure

**Files to Create:**
1. `backend/app/modules/governance/notifications/manager.py` - Notification manager
2. `backend/app/modules/governance/notifications/models.py` - Notification models
3. `backend/app/modules/governance/notifications/templates.py` - Email/Slack templates
4. `backend/app/modules/governance/notifications/channels/` - Channel implementations
   - `email.py` - SMTP email sender
   - `webhook.py` - Generic webhook
   - `slack.py` - Slack integration
   - `discord.py` - Discord integration

**Models:**
```python
class NotificationChannel(str, Enum):
    EMAIL = "email"
    WEBHOOK = "webhook"
    SLACK = "slack"
    DISCORD = "discord"

class NotificationEvent(str, Enum):
    APPROVAL_REQUESTED = "approval_requested"
    APPROVAL_APPROVED = "approval_approved"
    APPROVAL_REJECTED = "approval_rejected"
    APPROVAL_EXPIRING = "approval_expiring"
    APPROVAL_EXPIRED = "approval_expired"

class NotificationPreference(BaseModel):
    user_id: str
    channels: List[NotificationChannel]
    events: List[NotificationEvent]
    enabled: bool = True

class Notification(BaseModel):
    notification_id: str
    event: NotificationEvent
    approval_id: str
    recipients: List[str]
    channels: List[NotificationChannel]
    sent_at: Optional[float]
    delivered: bool = False
    retry_count: int = 0
    error: Optional[str]
```

**Configuration (environment variables):**
```bash
# Email (SMTP)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=notifications@brain.ai
SMTP_PASSWORD=...
SMTP_FROM=BRAiN Governance <notifications@brain.ai>

# Webhook
WEBHOOK_URL=https://example.com/webhook
WEBHOOK_SECRET=...

# Slack
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...

# Discord
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...
```

#### Day 2: Notification Templates & Delivery

**Email Template Example:**
```html
<!DOCTYPE html>
<html>
<head>
  <style>
    body { font-family: Arial, sans-serif; }
    .header { background: #1e40af; color: white; padding: 20px; }
    .content { padding: 20px; }
    .footer { background: #f3f4f6; padding: 10px; }
    .button { background: #10b981; color: white; padding: 10px 20px; }
  </style>
</head>
<body>
  <div class="header">
    <h1>🔔 BRAiN Governance Alert</h1>
  </div>
  <div class="content">
    <h2>New Approval Request</h2>
    <p><strong>Type:</strong> {{ approval_type }}</p>
    <p><strong>Risk Tier:</strong> <span class="risk-{{ risk_tier }}">{{ risk_tier }}</span></p>
    <p><strong>Requested By:</strong> {{ requested_by }}</p>
    <p><strong>Description:</strong> {{ description }}</p>
    <p><strong>Expires:</strong> {{ expires_at }}</p>

    <a href="{{ approval_url }}" class="button">Review Approval</a>
  </div>
  <div class="footer">
    <p>BRAiN Governance System</p>
  </div>
</body>
</html>
```

**Slack Message Example:**
```json
{
  "text": "🔔 New Governance Approval Required",
  "blocks": [
    {
      "type": "header",
      "text": {
        "type": "plain_text",
        "text": "🔔 New Governance Approval"
      }
    },
    {
      "type": "section",
      "fields": [
        {
          "type": "mrkdwn",
          "text": "*Type:*\nIR Escalation"
        },
        {
          "type": "mrkdwn",
          "text": "*Risk:*\n🔴 HIGH"
        },
        {
          "type": "mrkdwn",
          "text": "*Requested By:*\nops_agent"
        },
        {
          "type": "mrkdwn",
          "text": "*Expires:*\n24 hours"
        }
      ]
    },
    {
      "type": "actions",
      "elements": [
        {
          "type": "button",
          "text": {
            "type": "plain_text",
            "text": "Review Approval"
          },
          "url": "https://brain.falklabs.de/governance"
        }
      ]
    }
  ]
}
```

#### Day 3: Integration with Governance Service

**Update `governance_service.py`:**
```python
from backend.app.modules.governance.notifications.manager import NotificationManager

class GovernanceService:
    def __init__(self):
        self.storage = GovernanceStorage()
        self.notification_manager = NotificationManager()

    async def request_approval(self, ...) -> Approval:
        # Create approval
        approval = await self.storage.create_approval(...)

        # Send notifications
        await self.notification_manager.notify(
            event=NotificationEvent.APPROVAL_REQUESTED,
            approval=approval
        )

        return approval

    async def approve_approval(self, ...) -> Approval:
        # Approve approval
        approval = await self.storage.approve_approval(...)

        # Notify requester
        await self.notification_manager.notify(
            event=NotificationEvent.APPROVAL_APPROVED,
            approval=approval,
            recipients=[approval.context.requested_by]
        )

        return approval
```

**API Endpoints:**
```python
# Notification preferences
POST   /api/governance/notifications/preferences
GET    /api/governance/notifications/preferences/{user_id}
PUT    /api/governance/notifications/preferences/{user_id}
DELETE /api/governance/notifications/preferences/{user_id}

# Test notifications
POST   /api/governance/notifications/test
```

### Phase 2: RBAC System (Days 4-6)

#### Day 4: RBAC Data Models & Storage

**Files to Create:**
1. `backend/app/modules/governance/rbac/models.py` - RBAC models
2. `backend/app/modules/governance/rbac/storage.py` - RBAC storage
3. `backend/app/modules/governance/rbac/service.py` - RBAC service
4. `backend/app/modules/governance/rbac/router.py` - RBAC API

**Models:**
```python
class Permission(str, Enum):
    APPROVE_IR_ESCALATION = "approve_ir_escalation"
    APPROVE_COURSE_PUBLISH = "approve_course_publish"
    APPROVE_CERTIFICATE_ISSUANCE = "approve_certificate_issuance"
    APPROVE_POLICY_OVERRIDE = "approve_policy_override"
    VIEW_AUDIT = "view_audit"
    EXPORT_AUDIT = "export_audit"
    MANAGE_ROLES = "manage_roles"
    VIEW_STATS = "view_stats"

class RoleName(str, Enum):
    ADMIN = "admin"
    APPROVER = "approver"
    AUDITOR = "auditor"
    VIEWER = "viewer"

class Role(BaseModel):
    role_name: RoleName
    display_name: str
    description: str
    permissions: List[Permission]
    priority: int  # Higher = more privileged

class Actor(BaseModel):
    actor_id: str
    email: Optional[str]
    full_name: Optional[str]
    roles: List[RoleName]
    active: bool = True
    created_at: float
    updated_at: float

class RoleAssignment(BaseModel):
    actor_id: str
    role_name: RoleName
    assigned_by: str
    assigned_at: float
```

**Predefined Roles:**
```python
PREDEFINED_ROLES = {
    RoleName.ADMIN: Role(
        role_name=RoleName.ADMIN,
        display_name="Administrator",
        description="Full system access",
        permissions=[p for p in Permission],  # All permissions
        priority=100
    ),
    RoleName.APPROVER: Role(
        role_name=RoleName.APPROVER,
        display_name="Approver",
        description="Can approve/reject approvals",
        permissions=[
            Permission.APPROVE_IR_ESCALATION,
            Permission.APPROVE_COURSE_PUBLISH,
            Permission.APPROVE_CERTIFICATE_ISSUANCE,
            Permission.VIEW_STATS,
        ],
        priority=50
    ),
    RoleName.AUDITOR: Role(
        role_name=RoleName.AUDITOR,
        display_name="Auditor",
        description="Read-only compliance access",
        permissions=[
            Permission.VIEW_AUDIT,
            Permission.EXPORT_AUDIT,
            Permission.VIEW_STATS,
        ],
        priority=30
    ),
    RoleName.VIEWER: Role(
        role_name=RoleName.VIEWER,
        display_name="Viewer",
        description="Read-only observer",
        permissions=[
            Permission.VIEW_STATS,
        ],
        priority=10
    ),
}
```

#### Day 5: Permission Checks & Enforcement

**Permission Decorator:**
```python
from functools import wraps
from fastapi import HTTPException

def require_permission(permission: Permission):
    """Decorator to require permission for endpoint."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract actor_id from request
            actor_id = kwargs.get("actor_id") or kwargs.get("request").headers.get("X-Actor-ID")

            # Check permission
            rbac_service = RBACService()
            if not await rbac_service.has_permission(actor_id, permission):
                raise HTTPException(
                    status_code=403,
                    detail=f"Permission denied: {permission.value} required"
                )

            return await func(*args, **kwargs)
        return wrapper
    return decorator

# Usage in router
@router.post("/approvals/{approval_id}/approve")
@require_permission(Permission.APPROVE_IR_ESCALATION)
async def approve_approval(approval_id: str, payload: ApprovalActionPayload):
    # Only called if actor has permission
    ...
```

**Update Governance Endpoints:**
```python
# Add permission checks to all governance endpoints
@router.post("/approvals/{approval_id}/approve")
@require_permission(Permission.APPROVE_IR_ESCALATION)
async def approve_approval(...): ...

@router.get("/audit")
@require_permission(Permission.VIEW_AUDIT)
async def get_audit(...): ...

@router.get("/audit/export")
@require_permission(Permission.EXPORT_AUDIT)
async def export_audit(...): ...
```

#### Day 6: RBAC API & UI Integration

**RBAC API Endpoints:**
```python
# Actors
GET    /api/governance/rbac/actors
POST   /api/governance/rbac/actors
GET    /api/governance/rbac/actors/{actor_id}
PUT    /api/governance/rbac/actors/{actor_id}
DELETE /api/governance/rbac/actors/{actor_id}

# Roles
GET    /api/governance/rbac/roles
GET    /api/governance/rbac/roles/{role_name}

# Role Assignments
POST   /api/governance/rbac/actors/{actor_id}/roles
DELETE /api/governance/rbac/actors/{actor_id}/roles/{role_name}
GET    /api/governance/rbac/actors/{actor_id}/permissions

# Permission Checks
POST   /api/governance/rbac/check-permission
```

**Frontend Integration:**
```typescript
// Add RBAC management to governance dashboard
// New page: frontend/control_deck/app/governance/rbac/page.tsx

export function RBACManagement() {
  const { data: actors } = useActors();
  const { data: roles } = useRoles();

  return (
    <div>
      <h1>RBAC Management</h1>

      <Tabs defaultValue="actors">
        <TabsList>
          <TabsTrigger value="actors">Actors</TabsTrigger>
          <TabsTrigger value="roles">Roles</TabsTrigger>
        </TabsList>

        <TabsContent value="actors">
          <ActorsList actors={actors} />
        </TabsContent>

        <TabsContent value="roles">
          <RolesList roles={roles} />
        </TabsContent>
      </Tabs>
    </div>
  );
}
```

---

## Testing Strategy

### Notification System Tests

**File:** `backend/tests/test_sprint17_notifications.py`

**Test Cases:**
1. ✅ Send email notification
2. ✅ Send webhook notification
3. ✅ Send Slack notification
4. ✅ Notification retry on failure
5. ✅ Notification preferences (user opted out)
6. ✅ Multi-channel notifications
7. ✅ Template rendering
8. ✅ Notification audit trail

### RBAC System Tests

**File:** `backend/tests/test_sprint17_rbac.py`

**Test Cases:**
1. ✅ Create actor with roles
2. ✅ Assign role to actor
3. ✅ Remove role from actor
4. ✅ Check permission (has permission)
5. ✅ Check permission (lacks permission)
6. ✅ Permission enforcement in endpoints
7. ✅ Admin has all permissions
8. ✅ Auditor cannot approve
9. ✅ Viewer has minimal permissions
10. ✅ RBAC audit trail

---

## Success Criteria

### Notification System
- [ ] Email notifications sent successfully
- [ ] Webhook notifications delivered
- [ ] Slack messages appear in channel
- [ ] Failed notifications retry automatically
- [ ] Notification preferences honored
- [ ] All notification events covered
- [ ] Notification audit trail complete

### RBAC System
- [ ] All predefined roles created
- [ ] Actors can be assigned multiple roles
- [ ] Permission checks enforce access control
- [ ] Admin has all permissions
- [ ] Auditor has read-only access
- [ ] Unauthorized actions return 403
- [ ] RBAC audit trail complete
- [ ] UI for RBAC management functional

---

## Migration Plan

### Backward Compatibility

**No Breaking Changes:**
- Existing approvals work without RBAC
- Default permission: Allow all (if RBAC disabled)
- Opt-in RBAC via environment variable

**Environment Variable:**
```bash
GOVERNANCE_RBAC_ENABLED=true  # Enable RBAC (default: false)
GOVERNANCE_NOTIFICATIONS_ENABLED=true  # Enable notifications (default: false)
```

**Gradual Rollout:**
1. Deploy notification system (disabled by default)
2. Test with opt-in users
3. Deploy RBAC system (disabled by default)
4. Create initial actors and roles
5. Enable RBAC in production

---

## Deployment Checklist

### Pre-Deployment
- [ ] All tests passing
- [ ] Documentation complete
- [ ] Code review
- [ ] Environment variables configured
- [ ] SMTP credentials configured
- [ ] Webhook endpoints configured
- [ ] Initial actors created

### Deployment Steps
```bash
# 1. Update environment variables
cat >> .env <<EOF
GOVERNANCE_RBAC_ENABLED=true
GOVERNANCE_NOTIFICATIONS_ENABLED=true
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=...
SMTP_PASSWORD=...
SLACK_WEBHOOK_URL=...
EOF

# 2. Restart backend
docker compose restart backend

# 3. Create initial admin actor
curl -X POST http://localhost:8000/api/governance/rbac/actors \
  -H "Content-Type: application/json" \
  -d '{
    "actor_id": "admin",
    "email": "admin@brain.ai",
    "full_name": "System Administrator",
    "roles": ["admin"]
  }'

# 4. Run tests
pytest backend/tests/test_sprint17_*.py -v

# 5. Test notifications
curl -X POST http://localhost:8000/api/governance/notifications/test \
  -H "Content-Type: application/json" \
  -d '{
    "recipient": "admin@brain.ai",
    "channel": "email"
  }'
```

### Post-Deployment
- [ ] Monitor notification delivery rates
- [ ] Review RBAC audit logs
- [ ] Verify permission enforcement
- [ ] Test email/Slack notifications
- [ ] Create additional actors

---

## Risk Assessment

### Technical Risks

| Risk | Impact | Mitigation |
|------|--------|-----------|
| Email delivery failures | High | Retry logic, fallback channels |
| RBAC misconfiguration | Critical | Default to deny, audit trail |
| Notification spam | Medium | Rate limiting, user preferences |
| SMTP credentials leak | Critical | Environment variables, secrets management |

### Operational Risks

| Risk | Impact | Mitigation |
|------|--------|-----------|
| Too many notifications | Medium | Smart batching, digest mode |
| Role assignment errors | High | Audit trail, rollback capability |
| Permission lockout | Critical | Emergency admin override |

---

## Future Enhancements (Sprint 18+)

### Notification System
- SMS notifications (Twilio)
- Push notifications (web/mobile)
- Notification batching (digest mode)
- Custom notification rules
- Notification analytics

### RBAC System
- Custom roles (beyond predefined)
- Fine-grained permissions
- Temporary role assignments
- Delegation workflows
- LDAP/SSO integration

---

## Timeline

| Day | Phase | Deliverable |
|-----|-------|-------------|
| 1 | Notifications | Core infrastructure, models |
| 2 | Notifications | Templates, delivery logic |
| 3 | Notifications | Integration with governance |
| 4 | RBAC | Data models, storage |
| 5 | RBAC | Permission checks, enforcement |
| 6 | RBAC | API endpoints, UI integration |
| 7 | Testing | Comprehensive test suite |
| 8 | Documentation | Complete sprint report |

**Total:** 8 days

---

## Conclusion

Sprint 17 transforms BRAiN's governance system into an **enterprise-ready platform**:

- 🔔 **Proactive notifications** eliminate approval bottlenecks
- 🔐 **RBAC enforcement** ensures proper access control
- 📧 **Multi-channel delivery** reaches stakeholders where they are
- 👥 **Team collaboration** supports multiple actors with clear roles
- 📊 **Complete audit trail** for notifications and RBAC changes

**Ready for:**
- Enterprise deployments with multiple teams
- Compliance requirements (SOC2, ISO27001)
- High-stakes governance workflows
- Multi-tenant environments

---

**Sprint 17: 🎯 Planning Complete**
**Next Step:** Implementation kickoff
**Estimated Duration:** 8 days
**Breaking Changes:** None (opt-in features)

🚀 **Let's build enterprise-grade governance!**
