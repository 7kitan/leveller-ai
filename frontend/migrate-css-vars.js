#!/usr/bin/env node

/**
 * CSS Variable Migration Script
 * Migrates legacy CSS variables to the new OKLCH design system
 */

const fs = require('fs');
const path = require('path');

// Define all replacement mappings
const replacements = [
  // ============================================================================
  // PHASE 1: Direct Color Mappings
  // ============================================================================
  { from: /var\(--color-accent-primary\)/g, to: 'var(--color-primary)' },
  { from: /var\(--color-accent-secondary\)/g, to: 'var(--color-secondary)' },
  { from: /var\(--color-text-main\)/g, to: 'var(--color-text-primary)' },
  { from: /var\(--color-panel-bg\)/g, to: 'var(--color-bg-elevated)' },
  { from: /var\(--color-bg-light\)/g, to: 'var(--color-bg-primary)' },
  
  // ============================================================================
  // PHASE 2: Shorthand Expansions
  // ============================================================================
  { from: /var\(--text-primary\)/g, to: 'var(--color-text-primary)' },
  { from: /var\(--text-secondary\)/g, to: 'var(--color-text-secondary)' },
  { from: /var\(--text-muted\)/g, to: 'var(--color-text-tertiary)' },
  { from: /var\(--bg-primary\)/g, to: 'var(--color-bg-primary)' },
  { from: /var\(--bg-secondary\)/g, to: 'var(--color-bg-secondary)' },
  { from: /var\(--bg-tertiary\)/g, to: 'var(--color-bg-tertiary)' },
  { from: /var\(--bg-hover\)/g, to: 'var(--color-bg-hover)' },
  { from: /var\(--border-subtle\)/g, to: 'var(--color-border-subtle)' },
  { from: /var\(--border-color\)/g, to: 'var(--color-border-default)' },
  { from: /var\(--accent-color\)/g, to: 'var(--color-primary)' },
  
  // ============================================================================
  // PHASE 3: Scale Value Mappings (undefined variables → OKLCH equivalents)
  // ============================================================================
  { from: /var\(--color-dark-900\)/g, to: 'var(--color-neutral-900)' },
  { from: /var\(--color-primary-700\)/g, to: 'var(--color-accent-700)' },
  { from: /var\(--color-primary-600\)/g, to: 'var(--color-accent-600)' },
  { from: /var\(--color-primary-800\)/g, to: 'var(--color-accent-800)' },
  { from: /var\(--color-error-700\)/g, to: 'var(--color-error-dark)' },
  { from: /var\(--color-warning-700\)/g, to: 'var(--color-warning-dark)' },
  { from: /var\(--color-success-700\)/g, to: 'var(--color-success-dark)' },
  { from: /var\(--color-surface-dark-1\)/g, to: 'var(--color-bg-secondary)' },
  
  // ============================================================================
  // PHASE 4: Remove Apple Design System Colors
  // ============================================================================
  { from: /var\(--color-apple-near-black\)/g, to: 'var(--color-neutral-900)' },
  { from: /var\(--color-apple-blue\)/g, to: 'var(--color-primary)' },
  { from: /var\(--color-apple-black\)/g, to: 'var(--color-neutral-900)' },
  
  // ============================================================================
  // PHASE 5: Remove Deleted Variables (gradients, shadows, easing)
  // ============================================================================
  // Gradients - remove entirely (user requested)
  { 
    from: /background:\s*var\(--gradient-primary\);?/g, 
    to: '/* gradient removed - use solid color instead */ background: var(--color-primary);' 
  },
  { 
    from: /background:\s*linear-gradient\([^)]*var\(--gradient-primary\)[^)]*\);?/g, 
    to: '/* gradient removed */ background: var(--color-primary);' 
  },
  { 
    from: /background:\s*var\(--gradient-sky\);?/g, 
    to: '/* gradient removed */ background: var(--color-primary);' 
  },
  { 
    from: /background:\s*linear-gradient\([^)]*var\(--gradient-sky\)[^)]*\);?/g, 
    to: '/* gradient removed */ background: var(--color-primary);' 
  },
  
  // Complex gradient patterns with accent-primary/secondary
  {
    from: /background:\s*linear-gradient\(135deg,\s*var\(--color-accent-primary\)\s*0%,\s*var\(--color-accent-secondary\)\s*100%\);?/g,
    to: '/* gradient removed */ background: var(--color-primary);'
  },
  
  // Shadow premium - remove
  { from: /var\(--shadow-premium\)/g, to: '0 10px 30px rgba(0, 0, 0, 0.1)' },
  
  // Easing premium - replace with standard easing
  { from: /var\(--ease-premium\)/g, to: 'cubic-bezier(0.4, 0, 0.2, 1)' },
  
  // Text RGB (legacy)
  { from: /var\(--text-rgb\)/g, to: 'var(--color-text-primary)' },
];

/**
 * Apply all replacements to a file's content
 */
function migrateContent(content, filename) {
  let modified = content;
  let changeCount = 0;
  
  replacements.forEach(({ from, to }) => {
    const matches = modified.match(from);
    if (matches) {
      changeCount += matches.length;
      modified = modified.replace(from, to);
    }
  });
  
  return { content: modified, changeCount };
}

/**
 * Migrate a single CSS file
 */
function migrateFile(filePath) {
  const content = fs.readFileSync(filePath, 'utf8');
  const { content: newContent, changeCount } = migrateContent(content, path.basename(filePath));
  
  if (changeCount > 0) {
    fs.writeFileSync(filePath, newContent, 'utf8');
    console.log(`✓ ${filePath}: ${changeCount} replacements`);
    return changeCount;
  } else {
    console.log(`  ${filePath}: no changes needed`);
    return 0;
  }
}

/**
 * Find all CSS files recursively
 */
function findCSSFiles(dir, fileList = []) {
  const files = fs.readdirSync(dir);
  
  files.forEach(file => {
    const filePath = path.join(dir, file);
    const stat = fs.statSync(filePath);
    
    if (stat.isDirectory()) {
      // Skip node_modules, .next, etc.
      if (!file.startsWith('.') && file !== 'node_modules' && file !== '.next') {
        findCSSFiles(filePath, fileList);
      }
    } else if (file.endsWith('.css') || file.endsWith('.module.css')) {
      fileList.push(filePath);
    }
  });
  
  return fileList;
}

/**
 * Main execution
 */
function main() {
  const srcDir = path.join(__dirname, 'src');
  
  console.log('🔍 Finding CSS files...\n');
  const cssFiles = findCSSFiles(srcDir);
  console.log(`Found ${cssFiles.length} CSS files\n`);
  
  console.log('🔄 Migrating CSS variables...\n');
  let totalReplacements = 0;
  
  cssFiles.forEach(file => {
    totalReplacements += migrateFile(file);
  });
  
  console.log(`\n✅ Migration complete!`);
  console.log(`   Total replacements: ${totalReplacements}`);
  console.log(`   Files processed: ${cssFiles.length}`);
}

// Run the migration
main();
