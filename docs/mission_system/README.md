# 🧠 BRAIN Mission System V1

**Status:** Ready for Deployment
**Version:** 1.0.0
**Created:** 2025-11-11

---

## 📦 Was ist enthalten?

### Core Components:
```
✅ LLM Abstraction Layer (Mock-Client für V1)
✅ Mission Models (Pydantic Schemas)
✅ Redis Priority Queue (ZSET-basiert)
✅ Mission Orchestrator (Agent Assignment)
✅ Mission Executor (Execution Engine)
✅ Mission Evaluator (KARMA Integration)
✅ Mock Data Loader (Odoo-Style)
```

### API Endpoints:
```
✅ POST   /api/missions/create
✅ GET    /api/missions/{mission_id}
✅ GET    /api/missions/{mission_id}/status
✅ POST   /api/missions/{mission_id}/cancel
✅ GET    /api/missions/orchestrator/stats
✅ GET    /api/missions/queue/stats
✅ GET    /api/missions/active/list
```

---

## 🚀 Installation

### 1. Upload via WinSCP
```
1. Entpacke mission_system_v1.tar.gz auf deinem PC
2. Öffne WinSCP → Verbinde zu brain.falklabs.de
3. Navigiere zu /opt/brain/
4. Upload gesamten Ordner "mission_system_v1"
```

### 2. Deployment auf Server
```bash
ssh root@brain.falklabs.de

cd /opt/brain/mission_system_v1
chmod +x deploy.sh
./deploy.sh
```

### 3. Verify Installation
```bash
# Check Services
docker compose ps

# Check Logs
docker compose logs backend -f

# Test API
curl https://brain.falklabs.de/api/missions/queue/stats
```

---

## 📚 Architektur

### Priority Scoring
```python
score = (priority * 1000) + (age_minutes * 0.1) + (credits * 0.01)

Beispiel:
- Priority: HIGH (8) → 8000 points
- Age: 30 min → +3 points
- Credits: 200 → +2 points
= Total Score: 8005
```

### Agent Assignment
```python
1. Filter by Skills:
   required_skills = ["booking_data", "sms_gateway"]
   → Nur Agenten die diese Skills haben

2. Sort by Load + Credits:
   → Agent mit niedrigster Load
   → Bei gleichem Load: Höchste Credits (KARMA)
```

### Mission Lifecycle
```
CREATED → QUEUED → ASSIGNED → IN_PROGRESS
         ↓
    COMPLETED / FAILED / CANCELLED
         ↓
    (Optional: RETRY → zurück zu QUEUED)
```

---

## 🧪 Testing

### 1. Create Test Mission
```bash
curl -X POST https://brain.falklabs.de/api/missions/create \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test Late Check-in",
    "type": "guest_support",
    "tags": ["late_checkin", "urgent"],
    "required_skills": ["booking_data", "sms_gateway"],
    "priority": 8,
    "payload": {
      "guest_name": "Test Guest",
      "arrival_time": "23:30"
    }
  }'
```

### 2. Check Queue
```bash
curl https://brain.falklabs.de/api/missions/queue/stats
```

### 3. Get Mission Status
```bash
curl https://brain.falklabs.de/api/missions/{mission_id}/status
```

---

## 🔧 Configuration

### Environment Variables (.env)
```bash
# Redis
REDIS_URL=redis://redis:6379/0

# Mission System
MISSION_QUEUE_NAME=mission_queue
MISSION_MAX_RETRIES=3
MISSION_TIMEOUT_HOURS=2

# LLM (für später)
LLM_CLIENT_TYPE=mock
# LLM_API_KEY=xxx (später)
```

---

## 📊 Monitoring

### Queue Stats
```bash
GET /api/missions/queue/stats

Response:
{
  "total_missions": 15,
  "by_status": {
    "queued": 10,
    "processing": 5
  },
  "by_priority": {
    "HIGH": 8,
    "NORMAL": 7
  },
  "oldest_mission_age_minutes": 12.5
}
```

### Orchestrator Stats
```bash
GET /api/missions/orchestrator/stats

Response:
{
  "total_assigned": 42,
  "total_completed": 38,
  "total_failed": 4,
  "success_rate": 0.9,
  "by_agent": {
    "late_checkin_support_agent": {
      "assigned": 15,
      "completed": 14,
      "failed": 1
    }
  }
}
```

---

## 🐛 Troubleshooting

### Mission stuck in QUEUED
```bash
# Check Redis Connection
docker compose exec backend python -c "import redis; r=redis.Redis(host='redis'); print(r.ping())"

# Check Queue Size
docker compose exec redis redis-cli ZCARD mission_queue
```

### No Agents Available
```bash
# Check Agent Registry
curl https://brain.falklabs.de/api/agents

# Start Health Agent (if stopped)
curl -X POST https://brain.falklabs.de/api/agents/health-monitor/start
```

### High Memory Usage
```bash
# Check Redis Memory
docker compose exec redis redis-cli INFO memory

# Clear Old Missions (optional)
docker compose exec redis redis-cli DEL mission_queue_stats:*
```

---

## 🔄 Next Steps

### Phase 2 (nach V1):
- [ ] Memory Layer Integration
- [ ] KARMA Agent Implementation
- [ ] Real LLM Client (Local/API)
- [ ] Micro-Agents (JSON-Config)
- [ ] Genesis Mechanism

### Phase 3:
- [ ] Odoo Connector
- [ ] Frontend Dashboard
- [ ] WebSocket Live-Updates
- [ ] Advanced Routing Logic

---

## 📞 Support

Bei Problemen:
1. Check Logs: `docker compose logs backend -f`
2. Check Redis: `docker compose logs redis -f`
3. Check API Health: `curl https://brain.falklabs.de/api/health`

---

**Built with ❤️ by Claude (Chief Developer)**
**FalkLabs / Vinatic AG - 2025**
