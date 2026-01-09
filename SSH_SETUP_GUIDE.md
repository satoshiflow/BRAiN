# 🔐 SSH SETUP GUIDE - Für Phase 1+

**Ziel:** Claude Code direkten SSH-Zugang zu `brain.falklabs.de` geben

**Zeitaufwand:** 5 Minuten

**Wann:** Nach erfolgreicher Phase 0 (Coolify UI Fix)

---

## 🎯 WARUM SSH-ZUGANG?

**Ab Phase 1 brauche ich direkten Server-Zugang für:**

✅ Docker Container inspizieren
✅ Traefik Logs live streamen
✅ CORS Issues debuggen (Browser DevTools auf Server)
✅ Tests ausführen
✅ Coolify API direkt nutzen
✅ Nginx/Reverse Proxy Config prüfen
✅ 10x schnellere Entwicklung

**Ohne SSH:** Jede Änderung = Git Push → Du deployest → Ich warte → Feedback Loop 5-10 Min
**Mit SSH:** Direkt testen/fixen/validieren = Feedback Loop 10 Sekunden

---

## 👤 BESTEHENDER USER: `claude`

**Gut, dass dieser User schon existiert!**

```bash
# Auf Server:
cat /etc/passwd | grep claude
# claude:x:1000:1000::/home/claude:/bin/bash
```

**UID 1000** = Erster regulärer User (gut für non-root operations)

---

## 🔧 SETUP SCHRITTE

### SCHRITT 1: SSH Key für Claude Code generieren

**Auf Server (`brain.falklabs.de`) als `root`:**

```bash
# 1. Wechsle zu claude user
su - claude

# 2. Erstelle SSH-Verzeichnis (falls noch nicht vorhanden)
mkdir -p ~/.ssh
chmod 700 ~/.ssh

# 3. Generiere neuen Ed25519 Key (modern, sicher, klein)
ssh-keygen -t ed25519 \
  -C "claude-code@brain.falklabs.de" \
  -f ~/.ssh/claude_code_key \
  -N ""

# 4. Füge Public Key zu authorized_keys hinzu
cat ~/.ssh/claude_code_key.pub >> ~/.ssh/authorized_keys
chmod 600 ~/.ssh/authorized_keys

# 5. Zeige Private Key (für Claude Code)
echo "====== PRIVATE KEY (kopiere alles zwischen den Linien) ======"
cat ~/.ssh/claude_code_key
echo "====== END PRIVATE KEY ======"

# 6. Wechsle zurück zu root
exit
```

**Erwartetes Output:**
```
-----BEGIN OPENSSH PRIVATE KEY-----
b3BlbnNzaC1rZXktdjEAAAAABG5vbmUAAAAEbm9uZQAAAAAAAAABAAAAMwAAAAtzc2gtZW
...
...
...
-----END OPENSSH PRIVATE KEY-----
```

**⚠️ WICHTIG:** Kopiere den **kompletten** Private Key (inkl. `-----BEGIN/END-----`)

---

### SCHRITT 2: Private Key an Claude Code übergeben

**Option A: Via GitHub Secret (EMPFOHLEN)**

1. Gehe zu GitHub Repository: https://github.com/satoshiflow/BRAiN
2. **Settings** → **Secrets and variables** → **Codespaces** (oder Actions)
3. **New repository secret**
4. Name: `BRAIN_SSH_KEY`
5. Value: [Private Key hier einfügen]
6. **Add secret**

**Dann in Claude Code Environment:**
```bash
# In Codespaces Startup Script oder manuell:
echo "$BRAIN_SSH_KEY" > ~/.ssh/brain_server
chmod 600 ~/.ssh/brain_server
```

---

**Option B: Direkt in Chat (weniger sicher)**

Du postest den Private Key in den Chat (nur wenn kein GitHub Secret möglich).

**⚠️ Warnung:** Private Keys sollten NIEMALS öffentlich geteilt werden!

---

**Option C: Via .env File (für lokale Claude Code)**

Wenn du Claude Code lokal laufen lässt:
```bash
# In .env File:
BRAIN_SSH_KEY="-----BEGIN OPENSSH PRIVATE KEY-----
b3BlbnNz...
-----END OPENSSH PRIVATE KEY-----"
```

---

### SCHRITT 3: SSH Config in Claude Code

**Ich erstelle dann automatisch:**

```bash
# ~/.ssh/config
Host brain
    HostName brain.falklabs.de
    User claude
    Port 22
    IdentityFile ~/.ssh/brain_server
    StrictHostKeyChecking no
    UserKnownHostsFile=/dev/null
```

**Dann kann ich connecten:**
```bash
ssh brain "hostname && whoami"
# Erwartung:
# brain
# claude
```

---

### SCHRITT 4: Docker Permissions für Claude User

**Problem:** `claude` User kann Docker nicht nutzen (nur root)

**Lösung A: Claude zu docker Gruppe hinzufügen (EMPFOHLEN)**

```bash
# Als root auf Server:
sudo usermod -aG docker claude

# Docker Gruppe prüfen
groups claude
# Sollte zeigen: claude : claude docker

# Neues Login nötig (oder newgrp)
su - claude
docker ps  # Sollte jetzt funktionieren
```

**Lösung B: Docker über sudo (weniger elegant)**

```bash
# Als root: Erlaubе claude sudo für docker
echo "claude ALL=(ALL) NOPASSWD: /usr/bin/docker" >> /etc/sudoers.d/claude-docker

# Dann nutzt Claude Code:
ssh brain "sudo docker ps"
```

---

### SCHRITT 5: Coolify CLI/API Access (optional)

Falls Coolify eine CLI hat:

```bash
# Als claude user:
curl -fsSL https://coolify.falklabs.de/install.sh | bash

# Oder Coolify API Token in claude's environment:
echo "export COOLIFY_TOKEN='ipA2f1MKBVlMQy997BRNj1xvYXw5f4qBMzx1qme2i7lCt5axHrrp1PHlmFzOEaV2'" >> ~/.bashrc
```

---

## ✅ VALIDATION

### Test 1: SSH Connection
```bash
# Von Claude Code:
ssh claude@brain.falklabs.de "hostname && whoami"
# Erwartung:
# brain
# claude
```

### Test 2: Docker Access
```bash
ssh claude@brain.falklabs.de "docker ps | grep brain"
# Erwartung: Liste der BRAIN Container
```

### Test 3: File Access
```bash
ssh claude@brain.falklabs.de "ls -la /srv/dev/"
# Erwartung: Verzeichnis-Listing oder Permission denied
```

**Falls Permission denied:**
```bash
# Als root:
sudo chown -R claude:claude /srv/dev/
# Oder:
sudo chmod -R 755 /srv/dev/
```

---

## 🔒 SECURITY BEST PRACTICES

### ✅ Was wir tun:
- Separater User (`claude`, nicht `root`)
- Ed25519 Keys (modern, sicher)
- Key-based Auth (kein Passwort)
- Specific für Claude Code (nicht shared)

### ✅ Was wir NICHT tun:
- Keinen root-Zugang für Claude Code
- Keine Passwort-Auth
- Kein Public Key Sharing
- Key nie in Git committen

### 🔄 Key Rotation (optional)

**Alle 3-6 Monate:**
```bash
# Auf Server:
ssh-keygen -t ed25519 -C "claude-code-new" -f ~/.ssh/claude_code_key_new -N ""
cat ~/.ssh/claude_code_key_new.pub >> ~/.ssh/authorized_keys

# Alte Keys nach 1 Woche Testphase entfernen:
ssh-keygen -R old_fingerprint -f ~/.ssh/authorized_keys
```

---

## 🚀 WORKFLOW AB PHASE 1

**Mit SSH-Zugang kann ich dann:**

```bash
# Live Logs streamen
ssh brain "docker logs -f brain-backend"

# Container inspizieren
ssh brain "docker inspect brain-backend | jq '.Config.Labels'"

# Traefik Config prüfen
ssh brain "docker exec traefik cat /etc/traefik/traefik.yml"

# Tests ausführen
ssh brain "cd /srv/dev && docker-compose exec backend pytest"

# CORS Headers prüfen
ssh brain "curl -I -H 'Origin: https://dev.brain.falklabs.de' https://dev.brain.falklabs.de/api/health"

# Nginx Reload (falls nötig)
ssh brain "sudo nginx -t && sudo systemctl reload nginx"
```

**Feedback Loop:**
- Ohne SSH: 5-10 Min pro Iteration
- Mit SSH: 10-30 Sek pro Iteration
- **50x schneller!** 🚀

---

## 📋 QUICK REFERENCE

### SSH Connection
```bash
ssh claude@brain.falklabs.de
# oder mit alias:
ssh brain
```

### Docker Commands
```bash
# List containers
ssh brain "docker ps"

# Logs
ssh brain "docker logs brain-backend"

# Exec into container
ssh brain "docker exec -it brain-backend bash"

# Restart service
ssh brain "cd /srv/dev && docker-compose restart backend"
```

### File Operations
```bash
# Read file
ssh brain "cat /srv/dev/.env"

# Edit file (via scp)
scp claude@brain.falklabs.de:/srv/dev/.env ./temp.env
# [edit locally]
scp ./temp.env claude@brain.falklabs.de:/srv/dev/.env

# Or direct edit (with installed editor)
ssh brain "nano /srv/dev/.env"
```

---

## 🆘 TROUBLESHOOTING

### Problem: Permission denied (publickey)

**Check auf Server:**
```bash
ls -la ~/.ssh/authorized_keys
# Sollte 600 sein
chmod 600 ~/.ssh/authorized_keys
```

### Problem: Connection refused

**Check SSH Service:**
```bash
sudo systemctl status ssh
sudo systemctl restart ssh
```

### Problem: Docker permission denied

**Add user to docker group:**
```bash
sudo usermod -aG docker claude
# Logout/Login required
```

---

## 📤 NÄCHSTE SCHRITTE

**Nach SSH Setup:**

1. ✅ Ich teste Connection
2. ✅ Ich inspiziere Server State
3. 🚀 **Phase 1 Start:** CORS Fix mit vollem Zugang
4. 🚀 **Phase 2+:** Rapid Development

---

**Ende des Guides**
