# Task 2.7 - First-Time Setup Page

**Datum:** 2026-02-20  
**Status:** ✅ ABGESCHLOSSEN  
**Branch:** main (8b0c6f3)

---

## Übersicht

Die First-Time Setup Page ermöglicht die Erstellung des ersten Admin-Accounts bei initialer Installation.

---

## Datei

`frontend/control_deck/app/auth/setup/page.tsx`

---

## Funktionen

### 1. Setup-Check
- Prüft beim Laden ob bereits ein Admin existiert (`GET /api/auth/first-time-setup`)
- Wenn Admin existiert: Weiterleitung zu `/auth/signin`
- Wenn kein Admin: Setup-Formular anzeigen

### 2. Formular-Felder
| Feld | Validierung | Beschreibung |
|------|-------------|--------------|
| Email | Regex-Validierung | Admin E-Mail-Adresse |
| Username | Min 3 chars, alphanumeric + underscore | Login-Name |
| Full Name | Optional | Anzeigename |
| Password | Min 8 chars | Passwort |
| Confirm Password | Muss mit Password übereinstimmen | Passwort-Bestätigung |

### 3. Validierung
- Client-seitige Validierung vor Submit
- Email-Format prüfen
- Username-Länge und Zeichen prüfen
- Passwort-Länge prüfen
- Passwörter müssen übereinstimmen

### 4. States
- **Loading:** "Checking setup status..." mit Spinner
- **Error:** Alert-Box mit Fehlermeldung
- **Success:** Erfolgsmeldung + Auto-Redirect nach 2 Sekunden
- **Form:** Normales Eingabe-Formular

### 5. Auto-Login
- Nach erfolgreicher Registrierung wird der JWT-Token im localStorage gespeichert
- Automatische Weiterleitung zum Dashboard

---

## UI-Komponenten

- **Card:** Hauptcontainer mit Header und Content
- **Shield Icon:** Branding im Header
- **Form:** Mit Labels und Icons (Mail, User, Lock, UserCircle)
- **Alert:** Für Error-Meldungen
- **Button:** Submit mit Loading-State
- **Info Box:** Wichtiger Hinweis über einmaliges Setup

---

## API-Integration

### Check Setup Status
```typescript
GET /api/auth/first-time-setup
Response: { "needs_setup": true/false }
```

### Create First Admin
```typescript
POST /api/auth/first-time-setup
Body: {
  email: string,
  username: string,
  password: string,
  full_name: string | null
}
Response: {
  access_token: string,
  token_type: "bearer",
  user: UserResponse
}
```

---

## Routing

| Bedingung | Redirect |
|-----------|----------|
| Admin existiert | `/auth/signin` |
| Setup erfolgreich | `/dashboard` |

---

## Security

- Prüft Server-seitig ob Setup erlaubt ist (Backend schützt vor Doppel-Admin)
- Speichert Token sicher im localStorage
- Zeigt Warnung über einmaligen Setup-Prozess

---

## Testing

### Manuelle Tests:

1. [ ] Neue Installation → Setup-Seite wird angezeigt
2. [ ] Admin existiert → Redirect zu `/auth/signin`
3. [ ] Ungültige Email → Fehlermeldung
4. [ ] Username zu kurz → Fehlermeldung
5. [ ] Username mit Sonderzeichen → Fehlermeldung
6. [ ] Passwort zu kurz → Fehlermeldung
7. [ ] Passwörter unterschiedlich → Fehlermeldung
8. [ ] Gültige Daten → Success + Redirect
9. [ ] Token wird im localStorage gespeichert
10. [ ] Dashboard ist nach Setup erreichbar

---

## Integration mit anderen Tasks

- **Task 2.5:** Nutzt `GET/POST /api/auth/first-time-setup`
- **Task 2.8:** Nach Setup kann Admin Einladungen erstellen
- **Task 2.9:** Erstellter Admin kann User-Management nutzen

---

## Flow

```
User besucht /auth/setup
    ↓
Frontend prüft: GET /api/auth/first-time-setup
    ↓
Wenn needs_setup = false:
    → Redirect zu /auth/signin
Wenn needs_setup = true:
    → Zeige Setup-Formular
    ↓
User füllt Formular aus
    ↓
Frontend validiert Client-seitig
    ↓
Submit: POST /api/auth/first-time-setup
    ↓
Erfolg:
    → Token speichern
    → Success-State anzeigen
    → Redirect zu /dashboard (nach 2s)
Fehler:
    → Error-Alert anzeigen
```

---

## Git

```bash
Commit: 8b0c6f3
Message: feat(auth): Task 2.7 - First-Time Setup Page
Pushed to: origin/main
```

---

## Screenshots (Description)

### Loading State
- Centered Spinner mit "Checking setup status..."

### Setup Form
- Card mit Shield-Icon Header
- 5 Formular-Felder mit Icons
- Info-Box unten
- Submit-Button

### Success State
- Green CheckCircle Icon
- "Setup Complete!" Text
- "Redirecting to dashboard..." mit Spinner

---

## Abhängigkeiten

- Next.js (App Router)
- React (useState, useEffect)
- shadcn/ui Components
- Lucide Icons
- Fetch API

---

## Author

OpenClaw Agent (Kimi k2.5)  
Auftraggeber: OLi
