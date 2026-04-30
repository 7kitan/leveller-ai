#!/usr/bin/env node

/**
 * Fix hardcoded hex colors in student.module.css
 * Map them to OKLCH design system variables
 */

const fs = require('fs');
const path = require('path');

const filePath = path.join(__dirname, 'src/app/student/student.module.css');

// Color mapping: hex -> OKLCH variable
const colorMappings = [
  // Amber/Orange (Warning colors)
  { from: /#d97706/g, to: 'var(--color-warning-dark)' },
  { from: /#fbbf24/g, to: 'var(--color-warning)' },
  { from: /#f59e0b/g, to: 'var(--color-warning)' },
  { from: /#b45309/g, to: 'var(--color-warning-dark)' },
  
  // Cyan/Teal (Info colors)
  { from: /#22d3ee/g, to: 'var(--color-info)' },
  { from: /#06b6d4/g, to: 'var(--color-info)' },
  { from: /#0891b2/g, to: 'var(--color-info-dark)' },
  
  // Purple/Indigo (Primary/Accent colors)
  { from: /#8b5cf6/g, to: 'var(--color-primary)' },
  { from: /#a78bfa/g, to: 'var(--color-primary)' },
  { from: /#818cf8/g, to: 'var(--color-primary)' },
  { from: /#4f46e5/g, to: 'var(--color-primary)' },
  
  // Dark colors
  { from: /#0f172a/g, to: 'var(--color-neutral-900)' },
  
  // Green (Success)
  { from: /#10b981/g, to: 'var(--color-success)' },
  
  // RGBA patterns with hardcoded colors
  { from: /rgba\(245, 158, 11, 0\.05\)/g, to: 'color-mix(in oklch, var(--color-warning) 5%, transparent)' },
  { from: /rgba\(245, 158, 11, 0\.1\)/g, to: 'color-mix(in oklch, var(--color-warning) 10%, transparent)' },
  { from: /rgba\(245, 158, 11, 0\.2\)/g, to: 'color-mix(in oklch, var(--color-warning) 20%, transparent)' },
];

function fixColors() {
  let content = fs.readFileSync(filePath, 'utf8');
  let changeCount = 0;
  
  colorMappings.forEach(({ from, to }) => {
    const matches = content.match(from);
    if (matches) {
      changeCount += matches.length;
      content = content.replace(from, to);
    }
  });
  
  fs.writeFileSync(filePath, content, 'utf8');
  
  console.log(`✅ Fixed ${changeCount} hardcoded colors in student.module.css`);
}

fixColors();
