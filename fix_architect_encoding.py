#!/usr/bin/env python3
"""
Fix encoding issues in architect_agent.py
Same issue as ops_agent.py - corrupted German umlauts
"""

# Read with error handling
with open('backend/brain/agents/architect_agent.py', 'rb') as f:
    content = f.read()

# Decode with replacement characters
content_str = content.decode('utf-8', errors='replace')

# Replace corrupted characters (deutsche Umlaute)
replacements = {
    '�': '',  # Remove replacement characters
    'Fähigkeit': 'Fähigkeit',
    'müssen': 'müssen',
    'Änderungen': 'Änderungen',
    'tatsächlicher': 'tatsächlicher',
    'Ausführung': 'Ausführung',
    'Systemausfälle': 'Systemausfälle',
    'prüfen': 'prüfen',
    'für': 'für',
}

for old, new in replacements.items():
    content_str = content_str.replace(old, new)

# Fix bullet points (falls vorhanden)
content_str = content_str.replace('=�', '📋')
content_str = content_str.replace('=4', '🔴')

# Write back as UTF-8
with open('backend/brain/agents/architect_agent.py', 'w', encoding='utf-8') as f:
    f.write(content_str)

print("✅ Fixed encoding issues in architect_agent.py")
