# Connectors Module Enhancement Roadmap

**Version:** 1.0
**Created:** 2026-02-25
**Priority:** MEDIUM (foundation module, enables external integrations)

---

## Strategic Vision

The Connectors Module is the **"Synapse Layer"** that bridges BRAIN Core with external systems and human users. Current implementation is solid but has architectural gaps preventing:

1. **Dynamic connector registration** (requires app restart)
2. **Advanced routing** (all users get same connector)  
3. **Persistent conversation memory** (lost on session end)
4. **MCP integration** (can't expose connectors to Claude API)
5. **Event-driven workflows** (no reactive system)

This roadmap addresses these gaps in 5 strategic phases.

---

## Current State Assessment

### Strengths ✅
- **Clean architecture:** BaseConnector abstraction is well-designed
- **Unified interface:** All platforms use same message format
- **Security-first:** HMAC signing, env-based secrets, input validation
- **Multi-platform:** Telegram, WhatsApp, Voice, CLI all working
- **Proper auth:** All endpoints require `require_auth`

### Gaps ⚠️
- **In-memory registry:** Lost on restart
- **No persistence:** User preferences not stored
- **Limited routing:** No smart connector selection
- **No MCP:** Can't be used directly by Claude API
- **No events:** Connectors don't publish to event stream

### Security Considerations 🔒
- **Secrets management:** ✅ Environment variables only
- **Message signing:** ✅ HMAC-SHA256 implemented
- **Input validation:** ✅ Pydantic schemas with max_length
- **Rate limiting:** ✅ Per-connector quotas
- **Audit logging:** ❌ MISSING - Need to add
- **Conversation encryption:** ❌ MISSING - Need to add

---

## Phase 1: Persistent Registry (Weeks 1-2)

### Goal
Move connector registry from in-memory to PostgreSQL so connectors survive restarts.

### Implementation
```python
# New ORM model
class ConnectorORM(Base):
    id: str = Column(String, primary_key=True)
    type: str = Column(String)  # TELEGRAM, WHATSAPP, VOICE, CLI
    display_name: str = Column(String(255))
    status: str = Column(String)  # STOPPED, CONNECTED, ERROR
    config: JSON = Column(JSON)  # Platform-specific config
    created_at: datetime = Column(DateTime)
    last_heartbeat: datetime = Column(DateTime)

# Service changes
class ConnectorService:
    async def register(self, connector: BaseConnector) -> None:
        """Register connector in DB"""
        orm = ConnectorORM(
            id=connector.connector_id,
            type=connector.connector_type.value,
            display_name=connector.display_name,
            status=connector.status.value
        )
        db.add(orm)
        await db.commit()

    async def list_connectors(self) -> List[ConnectorInfo]:
        """Load from DB instead of memory"""
        orm_list = await db.query(ConnectorORM).all()
        return [self._orm_to_connector(orm) for orm in orm_list]
```

### Benefits
- Connectors persist across restarts
- Audit trail of connector lifecycle
- Multi-instance support (cloud-ready)

### Effort
**~3 days** - DB schema, ORM model, migration, service updates

### Testing
- Restart app, verify connectors still registered
- Test concurrent connector registration
- Verify status persistence

---

## Phase 2: MCP Server Integration (Weeks 3-5)

### Goal
Expose connectors as MCP servers so Claude API and other tools can use them.

### Implementation
```python
# New MCP adapter
class ConnectorMCPServer:
    """
    Exposes connector operations as MCP tools
    """
    def __init__(self, connector_service: ConnectorService):
        self.service = connector_service

    def tools(self) -> List[MCPTool]:
        return [
            MCPTool(
                name="send_message",
                description="Send message via connector",
                schema={
                    "connector_id": {"type": "string"},
                    "user_id": {"type": "string"},
                    "content": {"type": "string", "maxLength": 10000}
                }
            ),
            MCPTool(
                name="list_active_connectors",
                description="Get active connectors"
            ),
            MCPTool(
                name="get_connector_status",
                description="Check connector health"
            )
        ]

    async def send_message(self, connector_id: str, user_id: str, content: str):
        """MCP handler for sending messages"""
        connector = self.service.get(connector_id)
        message = OutgoingMessage(content=content)
        success = await connector.send_to_user(user_id, message)
        return {"success": success, "message_id": message.message_id}
```

### Benefits
- Claude API can directly send notifications
- External tools can integrate with BRAIN connectors
- Self-service connector wrapping for third-party devs

### Effort
**~1 week** - MCP spec implementation, testing, documentation

### Testing
- Claude API calls connector via MCP
- Third-party tools can integrate
- Performance testing under load

---

## Phase 3: Event Streaming (Weeks 5-7)

### Goal
Emit events for all connector operations to enable reactive workflows.

### Implementation
```python
# In BaseConnector
async def send_to_user(self, user_id: str, message: OutgoingMessage) -> bool:
    success = await self._platform_send(user_id, message)
    
    # Publish event
    await event_stream.publish(
        event_type="connector.message.sent",
        source="connectors",
        payload={
            "connector_id": self.connector_id,
            "user_id": user_id,
            "message_id": message.message_id,
            "content": message.content,
            "success": success
        }
    )
    return success

# New events published
Events:
- connector.started
- connector.stopped
- connector.error
- connector.message.received
- connector.message.sent
- connector.health.check (periodic)
```

### Benefits
- Mission Control can react to connector events
- Real-time dashboard updates
- Audit trail for compliance

### Effort
**~3 days** - Event schema definition, publishing points, testing

### Testing
- Event stream receives all expected events
- Dashboard updates in real-time
- Audit log completeness

---

## Phase 4: Advanced Routing (Weeks 7-9)

### Goal
Enable smart connector selection based on user preferences, context, and availability.

### Implementation
```python
# New schema
class ConnectorPreference(BaseModel):
    user_id: str
    connector_type: ConnectorType
    priority: int  # 1 = highest priority
    is_enabled: bool

# Router service
class ConnectorRouter:
    async def select_connector(
        self,
        user_id: str,
        notification_type: str = "standard",
        available_connectors: Optional[List[str]] = None
    ) -> Optional[str]:
        """
        Select best connector for user & context
        1. Check user preferences
        2. Filter by availability
        3. Return highest priority available
        """
        prefs = await db.query(ConnectorPreference)\
            .filter_by(user_id=user_id)\
            .order_by(ConnectorPreference.priority)\
            .all()
        
        for pref in prefs:
            if available_connectors and pref.connector_id in available_connectors:
                return pref.connector_id
        
        # Fallback to default (fastest available)
        return self._default_connector(available_connectors)

    async def send_notification(
        self,
        user_id: str,
        content: str,
        notification_type: str = "standard"
    ) -> bool:
        """Smart routing with fallback chain"""
        available = self.service.list_active()
        selected = await self.select_connector(
            user_id,
            notification_type,
            available
        )
        
        if not selected:
            logger.error(f"No available connector for {user_id}")
            return False
        
        connector = self.service.get(selected)
        message = OutgoingMessage(content=content)
        return await connector.send_to_user(user_id, message)
```

### Benefits
- Users can choose preferred communication channel
- Context-aware routing (urgent alerts via phone, regular via Telegram)
- Graceful degradation with fallbacks

### Effort
**~1 week** - Preference schema, router logic, UI for preferences

### Testing
- User preference persistence
- Smart routing selection logic
- Fallback chain behavior

---

## Phase 5: Persistent Conversation Memory (Weeks 9-12)

### Goal
Store conversation history so BRAIN remembers context across sessions.

### Implementation
```python
# New ORM model
class ConversationORM(Base):
    id: str = Column(String, primary_key=True)
    user_id: str = Column(String)
    connector_id: str = Column(String)
    created_at: datetime = Column(DateTime)
    last_updated: datetime = Column(DateTime)

class MessageHistoryORM(Base):
    id: str = Column(String, primary_key=True)
    conversation_id: str = Column(String, ForeignKey('conversations.id'))
    role: str = Column(String)  # "user" or "assistant"
    content: str = Column(String(10000))
    timestamp: datetime = Column(DateTime)
    metadata: JSON = Column(JSON)  # Embedding, sentiment, etc.

# Service
class ConversationService:
    async def add_to_history(
        self,
        user_id: str,
        connector_id: str,
        message: IncomingMessage
    ) -> str:
        """Add user message to history"""
        conv = await self.get_or_create_conversation(user_id, connector_id)
        
        history_orm = MessageHistoryORM(
            conversation_id=conv.id,
            role="user",
            content=message.content,
            timestamp=datetime.utcnow()
        )
        db.add(history_orm)
        await db.commit()
        return conv.id

    async def get_context(
        self,
        user_id: str,
        connector_id: str,
        limit: int = 10
    ) -> List[Dict]:
        """Retrieve recent conversation context"""
        conv = await self.get_or_create_conversation(user_id, connector_id)
        messages = await db.query(MessageHistoryORM)\
            .filter_by(conversation_id=conv.id)\
            .order_by(MessageHistoryORM.timestamp.desc())\
            .limit(limit)\
            .all()
        
        return [
            {"role": m.role, "content": m.content}
            for m in reversed(messages)
        ]

# In BaseConnector.send_to_brain()
async def send_to_brain(self, message: IncomingMessage) -> BrainResponse:
    # Get conversation context
    context = await conversation_service.get_context(
        user_id=message.sender_id,
        connector_id=self.connector_id
    )
    
    # Send to AXE with context
    response = await self._axe_request({
        "message": message.model_dump(),
        "context": context  # ← Conversation history
    })
    
    # Store response in history
    await conversation_service.add_to_history(
        user_id=message.sender_id,
        connector_id=self.connector_id,
        message=response,
        role="assistant"
    )
    
    return response
```

### Enhancements
- **Conversation Search:** Full-text search across history
- **Sentiment Analysis:** Track user sentiment over time
- **Topic Extraction:** Automatic conversation tagging
- **Privacy:** Optional auto-deletion after X days

### Benefits
- BRAIN remembers multi-session conversations
- Users get contextual responses
- Analytics on conversation patterns

### Effort
**~2 weeks** - DB schema, service layer, search index, privacy controls

### Testing
- Conversation persistence across restarts
- Context retrieval and accuracy
- Privacy deletion policies
- Search functionality

---

## Security Enhancements (Across All Phases)

### Phase 1: Audit Logging
```python
# New AuditLog model
class ConnectorAuditORM(Base):
    id: str = Column(String, primary_key=True)
    connector_id: str = Column(String)
    action: str = Column(String)  # send_message, start, stop, etc.
    principal_id: str = Column(String)  # Who initiated?
    timestamp: datetime = Column(DateTime)
    details: JSON = Column(JSON)
    result: str = Column(String)  # success, failure

# Log all sensitive operations
await audit_log.record(
    action="message_sent",
    connector_id="telegram_prod",
    principal_id=principal.principal_id,
    details={"user_id": user_id, "message_length": len(content)}
)
```

### Phase 2: Conversation Encryption
```python
# Encrypt sensitive fields at rest
class MessageHistoryORM(Base):
    content_encrypted: bytes  # Encrypted with fernet key
    
    def get_decrypted_content(self, key: bytes) -> str:
        cipher = Fernet(key)
        return cipher.decrypt(self.content_encrypted).decode()
```

### Phase 3: Fine-Grained RBAC
```python
class ConnectorPermission(str, Enum):
    VIEW = "view"           # Read connector status
    SEND = "send"           # Send messages via connector
    MANAGE = "manage"       # Start/stop connector
    ADMIN = "admin"         # Full control

# Check permission
if not await rbac_service.has_permission(
    principal_id=principal.principal_id,
    resource="connector:telegram_prod",
    action=ConnectorPermission.SEND
):
    raise HTTPException(403, "Not authorized to use this connector")
```

---

## Implementation Timeline

**Total Duration:** ~3 months (if parallel where possible)

```
Week 1-2:   Phase 1 (Persistent Registry)
Week 3-5:   Phase 2 (MCP Integration)
Week 5-7:   Phase 3 (Event Streaming) [parallel with Phase 2]
Week 7-9:   Phase 4 (Advanced Routing)
Week 9-12:  Phase 5 (Conversation Memory)
Throughout: Security enhancements
```

**Staffing:** 1-2 engineers, 1 security reviewer

---

## Success Metrics

- ✅ Connector registry persists across restarts
- ✅ Claude API can invoke connector operations
- ✅ All connector events published to event stream
- ✅ Users can configure connector preferences
- ✅ Conversation history retained & searchable
- ✅ 100% audit trail coverage
- ✅ Zero data loss on restart
- ✅ <100ms routing decision time

---

## Known Dependencies

- **Phase 1:** Database (already have PostgreSQL)
- **Phase 2:** MCP SDK / Protocol implementation
- **Phase 3:** Event stream infrastructure
- **Phase 4:** RBAC system (already have)
- **Phase 5:** Encryption library (fernet)

---

## Risks & Mitigation

| Risk | Severity | Mitigation |
|------|----------|-----------|
| Data loss during migration | HIGH | Test data recovery procedures, backup before each phase |
| Performance regression | MEDIUM | Load test before deploying each phase |
| Encryption key management | HIGH | Use dedicated KMS (AWS KMS, HashiCorp Vault) |
| Breaking API changes | MEDIUM | Versioning strategy (/v1, /v2) |

---

## Post-Implementation

**Monitoring:**
- Alert on connector downtime
- Track message latency
- Monitor event stream lag

**Maintenance:**
- Monthly security audits
- Quarterly connector re-certification
- Annual encryption key rotation

**Future Work:**
- SMS connector
- Email connector  
- Slack connector
- Webhook connector (for third-party integrations)

---

**Prepared By:** BRAIN Security Team
**Date:** 2026-02-25
**Status:** Ready for Phase 1 Planning
