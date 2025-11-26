# BRAIN Backend – Dev & Prod Setup

Dieses Dokument fasst zusammen, wie du (oder Claude) das BRAIN Backend lokal und in Docker startest.

---

## Struktur

Wichtige Dateien im Projektroot:

- `docker-compose.yml`            → Basis-Stack (Postgres, Redis, Qdrant, Backend, Nginx)
- `docker-compose.dev.yml`        → Dev-Overlay (Reload, Port 8010, Code-Mount)
- `docker-compose.prod.yml`       → Prod-Overlay (Port 8000, kein Reload)
- `.env.local`                    → lokale Dev-Umgebung
- `.env.prod`                     → Prod/Staging-Konfiguration
- `.venv/`                        → Python Virtualenv für lokale Entwicklung
- `brain.ps1`                     → PowerShell-Helfer (brain dev/prod/test)
- `backend/`                      → FastAPI-App (`backend.main:app`)

---

## 1. Lokale Entwicklung ohne Docker (nur Backend)

### 1.1 Virtualenv aktivieren

```powershell
cd D:\Hetzner\brain_modular_refactor
.\.venv\Scripts\Activate.ps1
