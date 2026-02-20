#!/bin/bash
# Add dynamic export to all page.tsx files

for file in $(find /home/oli/dev/brain-v2/frontend/control_deck/app -name "page.tsx" -o -name "page.ts" 2>/dev/null | grep -v node_modules); do
    # Check if file already has dynamic export
    if ! grep -q "export const dynamic" "$file"; then
        echo "Adding dynamic export to: $file"
        # Add after "use client" or at the top
        if head -1 "$file" | grep -q '"use client"'; then
            # Insert after first line
            sed -i '1a\
\
// Force dynamic rendering to prevent SSG useContext errors\
export const dynamic = '"'"'force-dynamic'"'"';' "$file"
        else
            # Insert at top
            sed -i '1i\
// Force dynamic rendering to prevent SSG useContext errors\
export const dynamic = '"'"'force-dynamic'"'"';\
' "$file"
        fi
    fi
done

echo "Done!"
