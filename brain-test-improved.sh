#!/bin/bash
# BRAiN Deployment Verification Script v2.0
# Mit Farben und intelligenter Fehlerbehandlung

# Farben
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
GRAY='\033[0;90m'
NC='\033[0m' # No Color

# Icons
OK="✅"
FAIL="❌"
WARN="⚠️"
INFO="ℹ️"

# Zähler
TOTAL_CHECKS=0
PASSED_CHECKS=0
FAILED_CHECKS=0

echo -e "${BLUE}==========================================${NC}"
echo -e "${CYAN}🧪 BRAiN Deployment Test Suite v2.0${NC}"
echo -e "${BLUE}==========================================${NC}"
echo ""

# ============================================================
# PHASE 1: Externe Erreichbarkeit (User-Perspektive)
# ============================================================
echo -e "${CYAN}📡 PHASE 1: Externe Erreichbarkeit testen${NC}"
echo -e "${GRAY}------------------------------------------${NC}"

echo -n "1.1 Backend API Health Check: "
RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" https://api.dev.brain.falklabs.de/api/health 2>&1)
TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
if [[ "$RESPONSE" == "200" ]]; then
    echo -e "${GREEN}${OK} HTTP $RESPONSE${NC}"
    PASSED_CHECKS=$((PASSED_CHECKS + 1))
elif [[ "$RESPONSE" == "405" ]]; then
    echo -e "${YELLOW}${WARN} HTTP $RESPONSE (Method Not Allowed - verwende GET statt HEAD)${NC}"
    PASSED_CHECKS=$((PASSED_CHECKS + 1))
elif [[ "$RESPONSE" == "503" ]]; then
    echo -e "${RED}${FAIL} HTTP $RESPONSE (Service Unavailable - Container gestoppt?)${NC}"
    FAILED_CHECKS=$((FAILED_CHECKS + 1))
elif [[ "$RESPONSE" == "504" ]]; then
    echo -e "${RED}${FAIL} HTTP $RESPONSE (Gateway Timeout - Traefik kann Service nicht erreichen)${NC}"
    FAILED_CHECKS=$((FAILED_CHECKS + 1))
else
    echo -e "${RED}${FAIL} HTTP $RESPONSE${NC}"
    FAILED_CHECKS=$((FAILED_CHECKS + 1))
fi

echo -n "1.2 Control Deck Frontend: "
RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" https://control.dev.brain.falklabs.de 2>&1)
TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
if [[ "$RESPONSE" =~ ^(200|307)$ ]]; then
    echo -e "${GREEN}${OK} HTTP $RESPONSE${NC}"
    PASSED_CHECKS=$((PASSED_CHECKS + 1))
elif [[ "$RESPONSE" == "503" ]]; then
    echo -e "${RED}${FAIL} HTTP $RESPONSE (Service Unavailable)${NC}"
    FAILED_CHECKS=$((FAILED_CHECKS + 1))
elif [[ "$RESPONSE" == "504" ]]; then
    echo -e "${RED}${FAIL} HTTP $RESPONSE (Gateway Timeout)${NC}"
    FAILED_CHECKS=$((FAILED_CHECKS + 1))
else
    echo -e "${RED}${FAIL} HTTP $RESPONSE${NC}"
    FAILED_CHECKS=$((FAILED_CHECKS + 1))
fi

echo -n "1.3 AXE UI Frontend: "
RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" https://axe.dev.brain.falklabs.de 2>&1)
TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
if [[ "$RESPONSE" == "200" ]]; then
    echo -e "${GREEN}${OK} HTTP $RESPONSE${NC}"
    PASSED_CHECKS=$((PASSED_CHECKS + 1))
elif [[ "$RESPONSE" == "503" ]]; then
    echo -e "${RED}${FAIL} HTTP $RESPONSE (Service Unavailable)${NC}"
    FAILED_CHECKS=$((FAILED_CHECKS + 1))
elif [[ "$RESPONSE" == "504" ]]; then
    echo -e "${RED}${FAIL} HTTP $RESPONSE (Gateway Timeout)${NC}"
    FAILED_CHECKS=$((FAILED_CHECKS + 1))
else
    echo -e "${RED}${FAIL} HTTP $RESPONSE${NC}"
    FAILED_CHECKS=$((FAILED_CHECKS + 1))
fi

echo ""

# ============================================================
# PHASE 2: Container Status (Docker-Ebene)
# ============================================================
echo -e "${CYAN}🐳 PHASE 2: Container Status prüfen${NC}"
echo -e "${GRAY}------------------------------------------${NC}"

CONTAINER_COUNT=$(docker ps --filter "name=mw0ck04s8go048c0g4so48cc" --format "{{.Names}}" | wc -l)
TOTAL_CHECKS=$((TOTAL_CHECKS + 1))

if [ "$CONTAINER_COUNT" -eq 0 ]; then
    echo -e "${RED}${FAIL} Keine BRAiN Container gefunden!${NC}"
    echo -e "${YELLOW}${WARN} Container sind gestoppt oder gelöscht. Deploy in Coolify starten!${NC}"
    FAILED_CHECKS=$((FAILED_CHECKS + 1))
else
    echo -e "${GREEN}${OK} $CONTAINER_COUNT BRAiN Container laufen${NC}"
    PASSED_CHECKS=$((PASSED_CHECKS + 1))
    echo ""
    docker ps --filter "name=mw0ck04s8go048c0g4so48cc" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
fi

echo ""

# Einzelne Container prüfen
for SERVICE in backend control_deck axe_ui; do
    echo -n "2.${SERVICE} Container: "
    CONTAINER=$(docker ps --filter "name=${SERVICE}" --format "{{.Names}}")
    TOTAL_CHECKS=$((TOTAL_CHECKS + 1))

    if [ -z "$CONTAINER" ]; then
        echo -e "${RED}${FAIL} Nicht gefunden${NC}"
        FAILED_CHECKS=$((FAILED_CHECKS + 1))
    else
        STATUS=$(docker ps --filter "name=${SERVICE}" --format "{{.Status}}")
        echo -e "${GREEN}${OK} $STATUS${NC}"
        PASSED_CHECKS=$((PASSED_CHECKS + 1))
    fi
done

echo ""

# ============================================================
# PHASE 3: Traefik Labels (Service Discovery)
# ============================================================
echo -e "${CYAN}🏷️  PHASE 3: Traefik Labels verifizieren${NC}"
echo -e "${GRAY}------------------------------------------${NC}"

for SERVICE in backend control_deck axe_ui; do
    echo -n "3.${SERVICE} Labels: "
    CONTAINER=$(docker ps --filter "name=${SERVICE}" -q)
    TOTAL_CHECKS=$((TOTAL_CHECKS + 1))

    if [ -z "$CONTAINER" ]; then
        echo -e "${GRAY}${INFO} Container nicht vorhanden - übersprungen${NC}"
        continue
    fi

    PORT_LABEL=$(docker inspect "$CONTAINER" | jq -r '.[0].Config.Labels["traefik.http.services.'${SERVICE}'.loadbalancer.server.port"]' 2>/dev/null)
    ROUTER_SERVICE=$(docker inspect "$CONTAINER" | jq -r '.[0].Config.Labels' | grep -o "traefik.http.routers.https.*${SERVICE}.service" | head -1)

    if [ "$PORT_LABEL" != "null" ] && [ -n "$ROUTER_SERVICE" ]; then
        echo -e "${GREEN}${OK} Port: $PORT_LABEL, Router-Binding vorhanden${NC}"
        PASSED_CHECKS=$((PASSED_CHECKS + 1))
    elif [ "$PORT_LABEL" != "null" ]; then
        echo -e "${YELLOW}${WARN} Port: $PORT_LABEL, aber Router-Binding fehlt!${NC}"
        FAILED_CHECKS=$((FAILED_CHECKS + 1))
    else
        echo -e "${RED}${FAIL} Labels fehlen oder unvollständig${NC}"
        FAILED_CHECKS=$((FAILED_CHECKS + 1))
    fi
done

echo ""

# ============================================================
# PHASE 4: DNS Auflösung (Docker Network)
# ============================================================
echo -e "${CYAN}🌐 PHASE 4: DNS Auflösung im Docker-Netzwerk${NC}"
echo -e "${GRAY}------------------------------------------${NC}"

for SERVICE in backend control_deck axe_ui; do
    echo -n "4.${SERVICE} DNS: "
    TOTAL_CHECKS=$((TOTAL_CHECKS + 1))

    DNS_RESULT=$(docker exec coolify-proxy nslookup ${SERVICE} 2>&1 | grep "Address:" | tail -1 | awk '{print $2}')

    if [[ "$DNS_RESULT" =~ ^10\. ]]; then
        echo -e "${GREEN}${OK} ${DNS_RESULT}${NC}"
        PASSED_CHECKS=$((PASSED_CHECKS + 1))
    else
        echo -e "${RED}${FAIL} Nicht auflösbar (Container läuft nicht?)${NC}"
        FAILED_CHECKS=$((FAILED_CHECKS + 1))
    fi
done

echo ""

# ============================================================
# PHASE 5: Direkte Container-Verbindung (Bypass Traefik)
# ============================================================
echo -e "${CYAN}🔌 PHASE 5: Direkte Container-Verbindung testen${NC}"
echo -e "${GRAY}------------------------------------------${NC}"

echo -n "5.1 Backend direkt: "
TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
RESPONSE=$(docker exec coolify-proxy wget -qO- http://backend:8000/api/health 2>&1 | head -n 1)
if [[ "$RESPONSE" == *"\"status\":\"ok\""* ]]; then
    echo -e "${GREEN}${OK} Backend antwortet${NC}"
    PASSED_CHECKS=$((PASSED_CHECKS + 1))
else
    echo -e "${RED}${FAIL} Keine Verbindung oder Container down${NC}"
    FAILED_CHECKS=$((FAILED_CHECKS + 1))
fi

echo -n "5.2 Control Deck direkt: "
TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
RESPONSE=$(docker exec coolify-proxy wget -qO- http://control_deck:3000 2>&1 | head -n 1)
if [[ "$RESPONSE" == *"<!DOCTYPE html>"* ]]; then
    echo -e "${GREEN}${OK} Control Deck antwortet${NC}"
    PASSED_CHECKS=$((PASSED_CHECKS + 1))
else
    echo -e "${RED}${FAIL} Keine Verbindung oder Container down${NC}"
    FAILED_CHECKS=$((FAILED_CHECKS + 1))
fi

echo -n "5.3 AXE UI direkt: "
TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
RESPONSE=$(docker exec coolify-proxy wget -qO- http://axe_ui:3000 2>&1 | head -n 1)
if [[ "$RESPONSE" == *"<!DOCTYPE html>"* ]]; then
    echo -e "${GREEN}${OK} AXE UI antwortet${NC}"
    PASSED_CHECKS=$((PASSED_CHECKS + 1))
else
    echo -e "${RED}${FAIL} Keine Verbindung oder Container down${NC}"
    FAILED_CHECKS=$((FAILED_CHECKS + 1))
fi

echo ""

# ============================================================
# PHASE 6: Container Logs (Fehlersuche)
# ============================================================
echo -e "${CYAN}📋 PHASE 6: Container Logs prüfen${NC}"
echo -e "${GRAY}------------------------------------------${NC}"

for SERVICE in backend control_deck axe_ui; do
    CONTAINER=$(docker ps --filter "name=${SERVICE}" -q)

    if [ -z "$CONTAINER" ]; then
        echo -e "6.${SERVICE}: ${GRAY}${INFO} Container nicht vorhanden - übersprungen${NC}"
        continue
    fi

    echo -e "${CYAN}6.${SERVICE} Logs (letzte 5 Zeilen):${NC}"
    docker logs "$CONTAINER" --tail 5 2>&1 | sed 's/^/  /'
    echo ""
done

# ============================================================
# ZUSAMMENFASSUNG
# ============================================================
echo ""
echo -e "${BLUE}==========================================${NC}"
echo -e "${CYAN}📊 Test-Zusammenfassung${NC}"
echo -e "${BLUE}==========================================${NC}"
echo ""

PASS_RATE=$((PASSED_CHECKS * 100 / TOTAL_CHECKS))

echo -e "Gesamt:   ${TOTAL_CHECKS} Tests"
echo -e "Bestanden: ${GREEN}${PASSED_CHECKS}${NC}"
echo -e "Fehlgeschlagen: ${RED}${FAILED_CHECKS}${NC}"
echo -e "Erfolgsquote: ${PASS_RATE}%"
echo ""

if [ "$PASS_RATE" -ge 90 ]; then
    echo -e "${GREEN}${OK} System läuft einwandfrei!${NC}"
elif [ "$PASS_RATE" -ge 70 ]; then
    echo -e "${YELLOW}${WARN} System läuft mit kleineren Problemen${NC}"
elif [ "$CONTAINER_COUNT" -eq 0 ]; then
    echo -e "${RED}${FAIL} Container sind gestoppt!${NC}"
    echo -e "${YELLOW}${WARN} Aktion: In Coolify 'Deploy All' starten${NC}"
else
    echo -e "${RED}${FAIL} Kritische Probleme erkannt!${NC}"
fi

echo ""
echo -e "${CYAN}💡 Diagnose-Hilfe:${NC}"
echo ""

# Intelligente Diagnose
if [ "$CONTAINER_COUNT" -eq 0 ]; then
    echo -e "${YELLOW}→ Container sind gestoppt oder gelöscht${NC}"
    echo -e "  ${CYAN}Lösung: Coolify UI → BRAiN Project → 'Deploy All'${NC}"
    echo ""
elif [ "$FAILED_CHECKS" -gt 0 ]; then
    # Prüfe ob externe Erreichbarkeit fehlt aber Container laufen
    BACKEND_STATUS=$(curl -s -o /dev/null -w "%{http_code}" https://api.dev.brain.falklabs.de/api/health 2>&1)
    BACKEND_CONTAINER=$(docker ps --filter "name=backend" -q)

    if [[ "$BACKEND_STATUS" == "504" ]] && [ -n "$BACKEND_CONTAINER" ]; then
        echo -e "${YELLOW}→ Container laufen, aber Traefik routet nicht (Gateway Timeout)${NC}"
        echo -e "  ${CYAN}Ursache: Traefik Service Discovery Cache-Problem${NC}"
        echo -e "  ${CYAN}Lösung: Container neu deployen (NICHT nur restart!)${NC}"
        echo -e "  ${GRAY}  docker stop <container> && docker rm <container>${NC}"
        echo -e "  ${GRAY}  Dann in Coolify: Service → Deploy${NC}"
        echo ""
    elif [[ "$BACKEND_STATUS" == "503" ]]; then
        echo -e "${YELLOW}→ Service Unavailable (503) - Container läuft nicht${NC}"
        echo -e "  ${CYAN}Lösung: Deployment starten${NC}"
        echo ""
    fi
fi

echo -e "${GRAY}Für Details: Einzelne Phasen oben prüfen${NC}"
