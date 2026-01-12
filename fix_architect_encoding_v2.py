#!/usr/bin/env python3
"""
Fix encoding issues in architect_agent.py - Version 2
More careful replacement strategy
"""

# Read with error handling
with open('backend/brain/agents/architect_agent.py', 'rb') as f:
    content = f.read()

# Decode with replacement characters
content_str = content.decode('utf-8', errors='replace')

# Fix the specific encoding issue on line 154 (max_tokens)
content_str = content_str.replace('max_tokens🔴096', 'max_tokens=4096')

# Fix line 89 (Versten -> Verstößen)
content_str = content_str.replace('Versten', 'Verstößen')

# Fix any other German umlauts that might be corrupted
# These are more targeted replacements
content_str = content_str.replace('F�higkeit', 'Fähigkeit')
content_str = content_str.replace('m�ssen', 'müssen')
content_str = content_str.replace('�nderungen', 'Änderungen')
content_str = content_str.replace('tats�chlicher', 'tatsächlicher')
content_str = content_str.replace('Ausf�hrung', 'Ausführung')
content_str = content_str.replace('Systemausf�lle', 'Systemausfälle')
content_str = content_str.replace('pr�fen', 'prüfen')
content_str = content_str.replace('f�r', 'für')

# Remove any remaining replacement characters that are standalone
content_str = content_str.replace('�', '')

# Write back as UTF-8
with open('backend/brain/agents/architect_agent.py', 'w', encoding='utf-8') as f:
    f.write(content_str)

print("✅ Fixed encoding issues in architect_agent.py (v2)")
