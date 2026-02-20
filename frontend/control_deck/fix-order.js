#!/usr/bin/env node
/**
 * Fix use client directive order in all page.tsx files
 * "use client" MUST be the first line
 */

const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

const appDir = '/home/oli/dev/brain-v2/frontend/control_deck/app';

function findPageFiles(dir) {
  const files = [];
  const items = fs.readdirSync(dir);
  
  for (const item of items) {
    const fullPath = path.join(dir, item);
    const stat = fs.statSync(fullPath);
    
    if (stat.isDirectory()) {
      files.push(...findPageFiles(fullPath));
    } else if (item === 'page.tsx' || item === 'page.ts') {
      files.push(fullPath);
    }
  }
  
  return files;
}

function fixFile(filePath) {
  const content = fs.readFileSync(filePath, 'utf-8');
  const lines = content.split('\n');
  
  // Check if has "use client" or 'use client'
  const useClientIndex = lines.findIndex(line => 
    line.trim() === '"use client"' || line.trim() === "'use client'"
  );
  
  if (useClientIndex === -1) {
    // No use client, file is fine
    return;
  }
  
  // Check if use client is at the very top
  if (useClientIndex === 0) {
    // Already correct
    return;
  }
  
  console.log(`Fixing: ${filePath}`);
  
  // Extract use client line (with correct quotes)
  const useClientLine = '"use client"';
  
  // Find and remove old use client line
  const newLines = lines.filter((line, idx) => 
    idx !== useClientIndex && 
    !line.includes("'use client'") &&
    !line.includes('"use client"')
  );
  
  // Remove empty comment line if present
  const cleanedLines = newLines.filter((line, idx) => {
    if (line.trim() === '// Force dynamic rendering to prevent SSG useContext errors') {
      // Keep the comment
      return true;
    }
    // Remove standalone dynamic export
    if (line.trim() === "export const dynamic = 'force-dynamic';") {
      return false;
    }
    return true;
  });
  
  // Build new content with correct order
  const dynamicComment = '// Force dynamic rendering to prevent SSG useContext errors';
  const dynamicExport = "export const dynamic = 'force-dynamic';";
  
  // Insert at beginning: use client, then dynamic
  cleanedLines.unshift(useClientLine, '', dynamicComment, dynamicExport);
  
  fs.writeFileSync(filePath, cleanedLines.join('\n'));
}

// Main
const pageFiles = findPageFiles(appDir);
console.log(`Found ${pageFiles.length} page files`);

for (const file of pageFiles) {
  fixFile(file);
}

console.log('Done!');
