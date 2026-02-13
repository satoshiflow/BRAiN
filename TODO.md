# BRAiN Development - TODO Liste

**Stand:** 2026-02-11  
**Nächste Session:** Control Deck + Mobile First

---

## 🔥 KRITISCH (Morgen)

### 1. Backend Stabilität (WICHTIG!)
- [ ] Root-Cause für Crashes finden (EventStream? Mission Worker?)
- [ ] Watchdog/Auto-Restart permanent implementieren
- [ ] Logs analysieren für wiederholbare Fehler

### 2. Control Deck - Funktionen
- [ ] API-Integration testen (Agents, Missions, Health)
- [ ] Datenanzeige verifizieren (nicht nur Mock-Daten)
- [ ] Mission erstellen/ausführen testen

---

## 🎨 HIGH PRIORITY (Diese Woche)

### 3. Control Deck - Usability & Mobile First
- [ ] Responsive Design (Tailwind Breakpoints)
- [ ] Mobile Navigation (Hamburger Menu)
- [ ] Touch-optimierte Buttons/Inputs
- [ ] Dark Mode (ist vorhanden, verifizieren)
- [ ] Loading States & Error Handling

### 4. AXE UI - API Connection
- [ ] Browser-Test: Warum zeigt es "Connecting..."?
- [ ] CORS/Proxy Fix (localhost vs 127.0.0.1)
- [ ] Fallback wenn Backend down

### 5. Python Bibliotheken erweitern
- [ ] `httpx` für Async HTTP
- [ ] `tenacity` für Retry-Logik
- [ ] `structlog` für bessere Logs
- [ ] `prometheus-client` für Metrics

---

## 🔒 SECURITY (Diese Woche)

### 6. AXE Gateway Security
- [ ] Prompt Injection Filter implementieren
- [ ] Input Sanitization (DOMPurify)
- [ ] Rate Limiting pro User
- [ ] Audit Logging (DB-Tabelle)

---

## 📱 MEDIUM PRIORITY (Nächste Woche)

### 7. Connectoren planen
- [ ] Telegram Bot Konzept
- [ ] WhatsApp Business API Konzept
- [ ] Email (SMTP/IMAP) Konzept

### 8. Mission System
- [ ] End-to-End Test
- [ ] Worker-Stabilität
- [ ] Queue-Persistenz

---

## 🚀 MORGENS STARTEN

### Wie startest du mich?
```bash
# Einfach im Terminal:
openclaw

# Oder falls nicht verfügbar:
cd /home/oli/.openclaw/workspace
# Dann: Deine Message an mich
```

**Wichtig:** Backend muss laufen vor dem Frontend-Test!
```bash
# Automatisch mit Sub-Agent:
curl -s http://127.0.0.1:8001/api/health || brain-start
```

---

## 📋 ERINNERUNG

**BRAiN = Autarkes System**  
**Fred = Dein Assistent zum Bauen**

Morgen: Control Deck + Mobile First + Backend-Stabilität

---

**Terminal kann zu.** Ich starte frisch morgen. 🚀
