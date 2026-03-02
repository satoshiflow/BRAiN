# 🔍 BRAiN Server Status Check

**Zweck:** Sicherheits-Check VOR jeder Änderung am Server

---

## ⚠️ WICHTIG: Erst checken, dann handeln!

Bevor wir irgendwas ändern, müssen wir wissen:
- Welcher User hat welche SSH Keys?
- Wo liegt was?
- Was läuft bereits?
- Was kann sicher gelöscht werden?

---

## 📋 SCHRITT 1: Status Check ausführen

### Auf Remote Server:

```bash
ssh root@brain.falklabs.de
cd /root/BRAiN

# Check-Script holen (falls nicht vorhanden)
git pull origin claude/update-claude-md-Q9jY6

# Check ausführen
bash check-server-status.sh
```

**Das Script prüft:**
1. ✅ **User:** root vs claude
2. ✅ **SSH Keys:** Wer hat welche Keys?
3. ✅ **Verzeichnisse:** Was existiert wo?
4. ✅ **Docker:** Was läuft?
5. ✅ **Cleanup Targets:** Was kann weg?
6. ✅ **Backups:** Was ist gesichert?
7. ✅ **Disk Space:** Wie viel Platz ist frei?

---

## 📊 Was das Script ausgibt:

### ✅ Grün = Alles OK
```
✅ User 'claude' exists
✅ /srv/dev/ exists
✅ Docker running
```

### ⚠️ Gelb = Warnung (aber OK)
```
⚠️ /root/BRAiN/ empty
⚠️ /opt/containerd/ exists (can be cleaned)
```

### ❌ Rot = Problem (muss geklärt werden)
```
❌ ERROR: /srv/dev does not exist
❌ User 'claude' does not exist
```

---

## 📋 SCHRITT 2: Output analysieren

Nach dem Check bekommst du einen Report mit:

### 1. User Analysis
- Welche User existieren?
- Wer hat welche Rechte?
- Wo sind die Home-Verzeichnisse?

### 2. SSH Key Analysis
- Root SSH Keys: Wo liegen sie?
- Claude SSH Keys: Wo liegen sie?
- GitHub Zugriff: Welcher User kann auf GitHub zugreifen?

### 3. Directory Structure
- `/root/BRAiN/` - Leer oder Git-Repo?
- `/srv/dev/` - Was liegt drin? Läuft es?
- `/srv/main/`, `/srv/stage/`, `/srv/prod/` - Leer?

### 4. Docker Status
- Welche Container laufen?
- Welche Ports sind belegt?
- Welche docker-compose Files existieren?

### 5. Cleanup Targets
- `/opt/brain-v2/` - Noch da oder weg?
- `/opt/containerd/` - Kann weg?
- `/opt/openwebui/` - Was ist drin?

### 6. Backups
- Was wurde gesichert?
- Wie viel Platz brauchen Backups?

### 7. Disk Space
- Wie viel Platz ist noch frei?

---

## 📋 SCHRITT 3: Report kopieren & mir schicken

### Output speichern:

```bash
bash check-server-status.sh > /root/server-status-report.txt 2>&1
```

### Report anschauen:

```bash
cat /root/server-status-report.txt
```

### Oder direkt Output kopieren und mir schicken

---

## 🎯 Was passiert danach?

### Basierend auf dem Report erstelle ich:

1. **Sicheres Setup-Script**
   - Berücksichtigt welcher User welche Keys hat
   - Respektiert bestehende Deployments
   - Macht NUR was nötig ist

2. **Angepasste Anweisungen**
   - Exakt auf deine Server-Situation zugeschnitten
   - Keine unnötigen Schritte
   - Keine Gefahr bestehende Systeme zu zerstören

---

## ✅ Erfolgskriterien

Nach dem Check sollten wir wissen:

- ✅ Welcher User (root/claude) hat GitHub SSH Zugriff?
- ✅ Ist `/srv/dev/` ein Git-Repo oder nur Files?
- ✅ Läuft Docker in `/srv/dev/` bereits?
- ✅ Ist `/root/BRAiN/` leer oder hat es schon was?
- ✅ Kann `/opt/containerd/` sicher gelöscht werden?
- ✅ Wo sind die OpenWebUI Config-Files?

---

## 🚦 Nächste Schritte:

1. ✅ **Check ausführen** (oben)
2. 📋 **Report mir schicken**
3. ⏳ **Warten** auf meine Analyse
4. 🎯 **Sicheres Script** von mir erhalten
5. ✅ **Ausführen** mit Vertrauen

---

**Kein Risiko. Erst verstehen, dann handeln.** 🛡️
