#!/usr/bin/env node
/**
 * Add dynamic export to all Client Components (pages with "use client")
 */

const fs = require('fs');
const path = require('path');

const appDir = '/home/oli/dev/brain-v2/frontend/control_deck/app';

function findPageFiles(dir) {
  const files = [];
  const items = fs.readdirSync(dir);
  
  for (const item of items) {
    const fullPath = path.join(dir, item);
    const stat = fs.statSync(fullPath);
    
    if (stat.isDirectory() && !item.includes('node_modules')) {
      files.push(...findPageFiles(fullPath));
    } else if ((item === 'page.tsx' || item === 'page.ts') && !fullPath.includes('node_modules')) {
      files.push(fullPath);
    }
  }
  
  return files;
}

function fixFile(filePath) {
  const content = fs.readFileSync(filePath, 'utf-8');
  
  // Check if has "use client" (not single quotes)
  if (!content.includes('"use client"')) {
    // Server component - skip
    return;
  }
  
  // Check if already has dynamic export
  if (content.includes("export const dynamic = 'force-dynamic'")) {
    return;
  }
  
  console.log(`Adding dynamic export to: ${filePath}`);
  
  // Add after "use client" line
  const newContent = content.replace(
    '"use client";',
    `"use client";

// Force dynamic rendering
export const dynamic = 'force-dynamic';`
  );
  
  fs.writeFileSync(filePath, newContent);
}

// Main
const pageFiles = findPageFiles(appDir);
console.log(`Found ${pageFiles.length} page files`);

let fixedCount = 0;
for (const file of pageFiles) {
  const before = fs.readFileSync(file, 'utf-8');
  fixFile(file);
  const after = fs.readFileSync(file, 'utf-8');
  if (before !== after) {
    fixedCount++;
  }
}

console.log(`Fixed ${fixedCount} files`);
