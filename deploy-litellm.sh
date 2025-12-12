#!/bin/bash
# Deploy LiteLLM Multi-Provider Setup
# Super einfach - macht alles automatisch!

set -e

echo "🚀 LiteLLM Multi-Provider Setup"
echo "================================"
echo ""

cd /opt/brain

# 1. Neueste Änderungen holen
echo "📥 1. Hole neueste Änderungen..."
git pull origin claude/migrate-v2-launch-01UQ1FuiVg8Rv6UQwwDar1g5
echo "✓ Repository aktualisiert"
echo ""

# 2. API Keys konfigurieren (optional)
echo "🔐 2. API Keys konfigurieren..."
if ! grep -q "OPENAI_API_KEY" .env 2>/dev/null; then
    echo "# LiteLLM API Keys (optional - leer lassen für nur Ollama)" >> .env
    echo "OPENAI_API_KEY=" >> .env
    echo "ANTHROPIC_API_KEY=" >> .env
    echo "✓ .env vorbereitet"
else
    echo "✓ API Keys bereits in .env"
fi
echo ""
echo "💡 Tipp: Editiere /opt/brain/.env um API Keys hinzuzufügen:"
echo "   nano /opt/brain/.env"
echo "   Füge hinzu: OPENAI_API_KEY=sk-..."
echo "               ANTHROPIC_API_KEY=sk-ant-..."
echo ""

# 3. Mehr Ollama Modelle herunterladen (optional)
echo "🤖 3. Ollama Modelle..."
CURRENT_MODELS=$(docker exec brain-ollama ollama list | tail -n +2 | wc -l)
echo "   Aktuelle Modelle: $CURRENT_MODELS"

if [ "$CURRENT_MODELS" -lt 2 ]; then
    echo ""
    echo "Möchtest du mehr Modelle herunterladen? (empfohlen)"
    echo "   1) llama3.2:3b (2GB) - Schnell, bereits heruntergeladen"
    echo "   2) qwen2.5:7b (4.7GB) - Sehr gut für Code"
    echo "   3) mistral:7b (4.1GB) - Allgemeine Aufgaben"
    echo ""
    read -p "Modell herunterladen? [2/3/n]: " choice

    case $choice in
        2)
            echo "Lade qwen2.5:7b herunter..."
            docker exec brain-ollama ollama pull qwen2.5:7b
            ;;
        3)
            echo "Lade mistral:7b herunter..."
            docker exec brain-ollama ollama pull mistral:7b
            ;;
        *)
            echo "Überspringe Modell-Download"
            ;;
    esac
fi
echo ""

# 4. LiteLLM starten
echo "🔄 4. Starte LiteLLM..."
docker compose up -d litellm
echo "✓ LiteLLM gestartet"
echo ""

# 5. Warte bis LiteLLM bereit ist
echo "⏳ 5. Warte auf LiteLLM..."
sleep 5

for i in {1..10}; do
    if curl -s http://localhost:4000/health > /dev/null 2>&1; then
        echo "✓ LiteLLM ist bereit!"
        break
    fi
    if [ $i -eq 10 ]; then
        echo "⚠️  LiteLLM braucht noch etwas Zeit..."
        echo "   Prüfe Status mit: docker compose logs litellm"
    fi
    sleep 2
done
echo ""

# 6. Status anzeigen
echo "📊 6. Status-Übersicht:"
echo "-------------------"
docker compose ps | grep -E "NAME|brain-ollama|brain-litellm|brain-openwebui"
echo ""

# 7. Verfügbare Modelle
echo "🤖 7. Verfügbare Modelle:"
echo "--------------------"
docker exec brain-ollama ollama list
echo ""

# 8. LiteLLM testen
echo "🧪 8. LiteLLM Test:"
echo "---------------"
echo "Health Check:"
curl -s http://localhost:4000/health | head -5
echo ""
echo ""

# 9. Konfiguration anzeigen
echo "✅ Setup komplett!"
echo "=================="
echo ""
echo "📋 Nächste Schritte:"
echo ""
echo "1️⃣  OpenWebUI mit LiteLLM verbinden:"
echo "   → Öffne: https://chat.falklabs.de"
echo "   → Settings → Connections"
echo "   → OpenAI API:"
echo "     - Base URL: http://litellm:4000"
echo "     - API Key: sk-brain-secret-key-change-this"
echo ""
echo "2️⃣  Verfügbare Modelle in LiteLLM:"
echo "   → llama3.2-3b (Ollama - lokal)"
echo "   → qwen2.5-7b (Ollama - lokal, falls installiert)"
echo "   → mistral-7b (Ollama - lokal, falls installiert)"
echo "   → gpt-4o (OpenAI - falls API Key gesetzt)"
echo "   → claude-3-5-sonnet (Anthropic - falls API Key gesetzt)"
echo ""
echo "3️⃣  Optional: API Keys hinzufügen:"
echo "   nano /opt/brain/.env"
echo "   # Dann Container neu starten:"
echo "   docker compose restart litellm"
echo ""
echo "📖 Logs anschauen:"
echo "   docker compose logs -f litellm"
echo ""
echo "🌐 URLs:"
echo "   OpenWebUI: https://chat.falklabs.de"
echo "   Control Deck: https://brain.falklabs.de"
echo "   LiteLLM API: http://localhost:4000"
echo ""
