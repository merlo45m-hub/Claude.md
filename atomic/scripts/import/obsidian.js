#!/usr/bin/env node
// scripts/import/obsidian.js
// Import notes from an Obsidian vault into Atomic

import { glob } from 'glob';
import { parse as parseYaml } from 'yaml';
import fs from 'fs';
import path from 'path';

import {
  getDefaultDbPath,
  openDatabase,
  prepareAtomInsert,
  prepareTagInsert,
  prepareAtomTagInsert,
  checkDuplicateBySourceUrl,
  getOrCreateTag,
  parseArgs,
  printSummary,
  generateId,
  now,
} from './shared/index.js';

const USAGE = `
Usage: node scripts/import/obsidian.js <vault_path> [options]

Import notes from an Obsidian vault into Atomic.

Arguments:
  vault_path              Path to the Obsidian vault folder

Options:
  --db <path>             Custom database path
  --max <n>               Maximum number of notes to import
  --exclude <pattern>     Additional glob patterns to exclude (can use multiple times)
  --dry-run               Show what would be imported without importing
  --json-output           Output results as JSON (for programmatic use)
  -h, --help              Show this help message

Examples:
  node scripts/import/obsidian.js ~/Documents/MyVault
  node scripts/import/obsidian.js ~/Documents/MyVault --max 100
  node scripts/import/obsidian.js ~/Documents/MyVault --exclude "Templates/**"
  node scripts/import/obsidian.js ~/Documents/MyVault --dry-run
`;

// Default patterns to exclude
const DEFAULT_EXCLUDES = [
  '.obsidian/**',
  '.trash/**',
  '.git/**',
  'node_modules/**',
];

/**
 * Parse YAML frontmatter from markdown content
 * @param {string} content - The full file content
 * @returns {{ frontmatter: Object|null, body: string }}
 */
function parseFrontmatter(content) {
  const frontmatterRegex = /^---\s*\n([\s\S]*?)\n---\s*\n?/;
  const match = content.match(frontmatterRegex);

  if (!match) {
    return { frontmatter: null, body: content };
  }

  try {
    const frontmatter = parseYaml(match[1]);
    const body = content.slice(match[0].length);
    return { frontmatter, body };
  } catch (error) {
    // If YAML parsing fails, treat as no frontmatter
    return { frontmatter: null, body: content };
  }
}

/**
 * Extract tags from frontmatter
 * Supports various formats: array, comma-separated string, nested
 * @param {Object|null} frontmatter - Parsed frontmatter
 * @returns {string[]} Array of tag names
 */
function extractFrontmatterTags(frontmatter) {
  if (!frontmatter || !frontmatter.tags) {
    return [];
  }

  const tags = frontmatter.tags;

  // Handle array format
  if (Array.isArray(tags)) {
    return tags.map(t => String(t).trim()).filter(Boolean);
  }

  // Handle comma-separated string
  if (typeof tags === 'string') {
    return tags.split(',').map(t => t.trim()).filter(Boolean);
  }

  return [];
}

/**
 * Extract tags from folder path
 * e.g., "Projects/Work/note.md" -> ["Projects", "Work"]
 * @param {string} relativePath - Path relative to vault root
 * @returns {string[]} Array of folder names as tags
 */
function extractFolderTags(relativePath) {
  const dir = path.dirname(relativePath);
  if (dir === '.') {
    return [];
  }
  return dir.split(path.sep).filter(Boolean);
}

/**
 * Get the vault name from the vault path
 * @param {string} vaultPath - Absolute path to vault
 * @returns {string} Vault name (folder name)
 */
function getVaultName(vaultPath) {
  return path.basename(path.resolve(vaultPath));
}

/**
 * Generate a source URL for deduplication and reference
 * @param {string} vaultName - Name of the vault
 * @param {string} relativePath - Path to note relative to vault
 * @returns {string} Obsidian-style URL
 */
function generateSourceUrl(vaultName, relativePath) {
  // Remove .md extension and encode path components
  const notePath = relativePath.replace(/\.md$/, '');
  return `obsidian://${encodeURIComponent(vaultName)}/${notePath.split(path.sep).map(encodeURIComponent).join('/')}`;
}

/**
 * Parse an Obsidian note file
 * @param {string} filePath - Absolute path to the file
 * @param {string} relativePath - Path relative to vault
 * @param {string} vaultName - Name of the vault
 * @returns {Object} Parsed note data
 */
function parseObsidianNote(filePath, relativePath, vaultName) {
  const content = fs.readFileSync(filePath, 'utf-8');
  const { frontmatter, body } = parseFrontmatter(content);

  // Get file stats for timestamps
  const stats = fs.statSync(filePath);

  // Extract title from frontmatter, first h1, or filename
  let title = null;
  if (frontmatter?.title) {
    title = frontmatter.title;
  } else {
    const h1Match = body.match(/^#\s+(.+)$/m);
    if (h1Match) {
      title = h1Match[1].trim();
    } else {
      title = path.basename(relativePath, '.md');
    }
  }

  // Build the final content - preserve wikilinks as-is per user preference
  // Add title as h1 if not already present
  let finalContent = body.trim();
  if (!finalContent.startsWith('# ')) {
    finalContent = `# ${title}\n\n${finalContent}`;
  }

  // Extract tags from both frontmatter and folder structure
  const frontmatterTags = extractFrontmatterTags(frontmatter);
  const folderTags = extractFolderTags(relativePath);
  const allTags = [...new Set([...folderTags, ...frontmatterTags])];

  return {
    title,
    content: finalContent,
    sourceUrl: generateSourceUrl(vaultName, relativePath),
    tags: allTags,
    createdAt: frontmatter?.created
      ? new Date(frontmatter.created).toISOString()
      : stats.birthtime.toISOString(),
    updatedAt: frontmatter?.modified || frontmatter?.updated
      ? new Date(frontmatter.modified || frontmatter.updated).toISOString()
      : stats.mtime.toISOString(),
    relativePath,
  };
}

/**
 * Discover all markdown files in the vault
 * @param {string} vaultPath - Path to vault
 * @param {string[]} excludePatterns - Patterns to exclude
 * @returns {Promise<string[]>} Array of relative file paths
 */
async function discoverNotes(vaultPath, excludePatterns) {
  const absoluteVaultPath = path.resolve(vaultPath);

  const files = await glob('**/*.md', {
    cwd: absoluteVaultPath,
    ignore: excludePatterns,
    nodir: true,
  });

  return files;
}

/**
 * Main import function
 */
async function importObsidianVault(vaultPath, options) {
  const { db: dbPath, max, dryRun, jsonOutput, exclude } = options;

  // Validate vault path
  const absoluteVaultPath = path.resolve(vaultPath);
  if (!fs.existsSync(absoluteVaultPath)) {
    console.error(`\nError: Vault not found at ${absoluteVaultPath}`);
    process.exit(1);
  }

  // Check if it looks like an Obsidian vault
  const obsidianConfigPath = path.join(absoluteVaultPath, '.obsidian');
  if (!fs.existsSync(obsidianConfigPath)) {
    if (!jsonOutput) {
      console.warn(`\nWarning: No .obsidian folder found. This may not be an Obsidian vault.`);
      console.warn(`Continuing anyway...\n`);
    }
  }

  const vaultName = getVaultName(absoluteVaultPath);

  if (!jsonOutput) {
    console.log(`Importing Obsidian vault: ${absoluteVaultPath}`);
    console.log(`Vault name: ${vaultName}\n`);
  }

  // Discover notes
  const excludePatterns = [...DEFAULT_EXCLUDES, ...exclude];
  const noteFiles = await discoverNotes(absoluteVaultPath, excludePatterns);

  if (!jsonOutput) {
    console.log(`Found ${noteFiles.length} markdown files`);
    if (excludePatterns.length > DEFAULT_EXCLUDES.length) {
      console.log(`Excluding patterns: ${excludePatterns.join(', ')}`);
    }
  }

  if (noteFiles.length === 0) {
    if (!jsonOutput) {
      console.log('\nNo notes to import!');
    }
    return { imported: 0, skipped: 0, errors: 0, tagsCreated: 0, tagsLinked: 0 };
  }

  // Limit number of notes if specified
  let notesToProcess = noteFiles;
  if (max && noteFiles.length > max) {
    notesToProcess = noteFiles.slice(0, max);
    if (!jsonOutput) {
      console.log(`Limiting to ${max} notes (out of ${noteFiles.length})`);
    }
  }

  // Dry run mode
  if (dryRun) {
    if (!jsonOutput) {
      console.log('\n--- DRY RUN MODE ---\n');
      console.log('Would import the following notes:\n');
      for (const relativePath of notesToProcess) {
        const note = parseObsidianNote(
          path.join(absoluteVaultPath, relativePath),
          relativePath,
          vaultName
        );
        console.log(`  ${relativePath}`);
        console.log(`    Title: ${note.title}`);
        console.log(`    Tags: ${note.tags.length > 0 ? note.tags.join(', ') : '(none)'}`);
        console.log(`    Content length: ${note.content.length} chars`);
        console.log('');
      }
      console.log(`Total: ${notesToProcess.length} notes would be imported`);
    } else {
      const notes = notesToProcess.map(relativePath => {
        const note = parseObsidianNote(
          path.join(absoluteVaultPath, relativePath),
          relativePath,
          vaultName
        );
        return { path: relativePath, title: note.title, tags: note.tags };
      });
      console.log(JSON.stringify({ dryRun: true, notes }));
    }
    return { imported: 0, skipped: 0, errors: 0, tagsCreated: 0, tagsLinked: 0, dryRun: true };
  }

  // Open database
  const resolvedDbPath = dbPath || getDefaultDbPath();
  if (!jsonOutput) {
    console.log(`\nOpening database at ${resolvedDbPath}`);
  }
  const db = openDatabase(resolvedDbPath);

  // Prepare statements
  const insertAtom = prepareAtomInsert(db);
  const insertTag = prepareTagInsert(db);
  const insertAtomTag = prepareAtomTagInsert(db);

  // Track statistics
  const stats = {
    imported: 0,
    skipped: 0,
    errors: 0,
    tagsCreated: 0,
    tagsLinked: 0,
  };

  // Tag cache to avoid repeated queries
  const tagCache = new Map();

  if (!jsonOutput) {
    console.log('\nImporting notes...\n');
  }

  // Process each note
  for (let i = 0; i < notesToProcess.length; i++) {
    const relativePath = notesToProcess[i];
    const filePath = path.join(absoluteVaultPath, relativePath);

    try {
      const note = parseObsidianNote(filePath, relativePath, vaultName);

      // Skip if content is too short (likely empty or template)
      if (note.content.trim().length < 10) {
        if (!jsonOutput) {
          console.log(`[${i + 1}/${notesToProcess.length}] Skipped (empty): ${relativePath}`);
        }
        stats.skipped++;
        continue;
      }

      // Check for duplicates by source URL
      if (checkDuplicateBySourceUrl(db, note.sourceUrl)) {
        if (!jsonOutput) {
          console.log(`[${i + 1}/${notesToProcess.length}] Skipped (duplicate): ${relativePath}`);
        }
        stats.skipped++;
        continue;
      }

      // Create atom
      const atomId = generateId();
      const timestamp = now();

      db.transaction(() => {
        // Insert atom
        insertAtom.run(
          atomId,
          note.content,
          note.sourceUrl,
          note.createdAt,
          note.updatedAt
        );

        // Create/link tags
        for (const tagName of note.tags) {
          let tagInfo = tagCache.get(tagName.toLowerCase());

          if (!tagInfo) {
            tagInfo = getOrCreateTag(db, tagName, null, insertTag);
            tagCache.set(tagName.toLowerCase(), tagInfo);

            if (tagInfo.isNew) {
              stats.tagsCreated++;
            }
          }

          insertAtomTag.run(atomId, tagInfo.id);
          stats.tagsLinked++;
        }
      })();

      stats.imported++;

      if (!jsonOutput) {
        const tagStr = note.tags.length > 0 ? ` [${note.tags.join(', ')}]` : '';
        console.log(`[${i + 1}/${notesToProcess.length}] Imported: ${note.title}${tagStr}`);
      }
    } catch (error) {
      stats.errors++;
      if (!jsonOutput) {
        console.error(`[${i + 1}/${notesToProcess.length}] Error: ${relativePath} - ${error.message}`);
      }
    }
  }

  db.close();

  // Print summary
  printSummary(stats, jsonOutput);

  return stats;
}

// Main entry point
async function main() {
  const args = parseArgs(process.argv.slice(2), {
    exclude: [],
  });

  if (args.help) {
    console.log(USAGE);
    process.exit(0);
  }

  if (args.positional.length === 0) {
    console.error(USAGE);
    process.exit(1);
  }

  const vaultPath = args.positional[0];

  await importObsidianVault(vaultPath, args);
}

main().catch((error) => {
  console.error(`\nFatal error: ${error.message}`);
  process.exit(1);
});
