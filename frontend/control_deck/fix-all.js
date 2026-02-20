#!/usr/bin/env node
/**
 * Fix ALL page.tsx files - remove wrong order, add correct order
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
  let content = fs.readFileSync(filePath, 'utf-8');
  
  // Check if has use client (single or double quotes)
  const hasUseClient = content.includes('"use client"') || content.includes("'use client'");
  
  if (!hasUseClient) {
    // Server component - dynamic export at top is fine
    return;
  }
  
  console.log(`Fixing: ${filePath}`);
  
  // Remove all dynamic export related lines
  content = content.replace(/\/\/ Force dynamic rendering.*\n/g, '');
  content = content.replace(/export const dynamic = 'force-dynamic';\n?/g, '');
  content = content.replace(/export const dynamic = "force-dynamic";\n?/g, '');
  content = content.replace(/"use client";\n?/g, '');
  content = content.replace(/'use client';\n?/g, '');
  
  // Remove leading empty lines
  content = content.replace(/^\n+/, '');
  
  // Add correct order at the beginning
  const newContent = `"use client";

// Force dynamic rendering to prevent SSG useContext errors
export const dynamic = 'force-dynamic';

${content}`;
  
  fs.writeFileSync(filePath, newContent);
}

// Main
const pageFiles = findPageFiles(appDir);
console.log(`Found ${pageFiles.length} page files`);

for (const file of pageFiles) {
  fixFile(file);
}

console.log('Done!');
