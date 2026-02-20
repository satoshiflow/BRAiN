#!/bin/bash
# Fix use client directive order in all page.tsx files

for file in $(find /home/oli/dev/brain-v2/frontend/control_deck/app -name "page.tsx" -o -name "page.ts" 2>/dev/null | grep -v node_modules); do
    # Check if file has use client
    if head -1 "$file" | grep -q '"use client"'; then
        # Check if dynamic export is BEFORE use client (wrong order)
        if head -3 "$file" | grep -q "export const dynamic"; then
            echo "Fixing order in: $file"
            
            # Create temp file with correct order
            # 1. use client
            # 2. empty line
            # 3. dynamic export
            # 4. rest of file
            
            # Extract the dynamic line
            dynamic_line=$(grep "export const dynamic" "$file")
            
            # Remove dynamic export line from file
            sed -i '/export const dynamic/d' "$file"
            sed -i '/Force dynamic rendering/d' "$file"
            
            # Insert after "use client"
            sed -i '1a\
\
// Force dynamic rendering to prevent SSG useContext errors\
'"$dynamic_line" "$file"
        fi
    fi
done

echo "Done fixing order!"
