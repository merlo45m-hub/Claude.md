// scripts/import/shared/index.js
// Shared utilities for import scripts

import Database from 'better-sqlite3';
import { randomUUID } from 'crypto';
import fs from 'fs';

/**
 * Get the default database path based on platform
 * For macOS: ~/Library/Application Support/com.atomic.app/atomic.db
 * For Linux: ~/.local/share/com.atomic.app/atomic.db
 * For Windows: %APPDATA%/com.atomic.app/atomic.db
 */
export function getDefaultDbPath() {
  const platform = process.platform;
  const home = process.env.HOME || process.env.USERPROFILE;

  if (platform === 'darwin') {
    return `${home}/Library/Application Support/com.atomic.app/atomic.db`;
  } else if (platform === 'linux') {
    return `${home}/.local/share/com.atomic.app/atomic.db`;
  } else if (platform === 'win32') {
    return `${process.env.APPDATA}/com.atomic.app/atomic.db`;
  }
  throw new Error(`Unsupported platform: ${platform}`);
}

/**
 * Open the database and verify it exists
 * @param {string} dbPath - Path to the database file
 * @returns {Database} The database instance
 */
export function openDatabase(dbPath) {
  if (!fs.existsSync(dbPath)) {
    console.error(`\nError: Database not found at ${dbPath}`);
    console.error('\nThe database is created when you first run the Atomic app.');
    console.error('Please run the app at least once before using this import script.');
    console.error('\nAlternatively, specify a custom database path with --db <path>');
    process.exit(1);
  }

  return new Database(dbPath);
}

/**
 * Prepare the insert statement for atoms
 * @param {Database} db - The database instance
 * @returns {Statement} Prepared statement for inserting atoms
 */
export function prepareAtomInsert(db) {
  return db.prepare(`
    INSERT INTO atoms (id, content, source_url, created_at, updated_at, embedding_status, tagging_status)
    VALUES (?, ?, ?, ?, ?, 'pending', 'pending')
  `);
}

/**
 * Prepare the insert statement for tags
 * @param {Database} db - The database instance
 * @returns {Statement} Prepared statement for inserting tags
 */
export function prepareTagInsert(db) {
  return db.prepare(`
    INSERT OR IGNORE INTO tags (id, name, parent_id, created_at)
    VALUES (?, ?, ?, ?)
  `);
}

/**
 * Prepare the insert statement for atom_tags relationship
 * @param {Database} db - The database instance
 * @returns {Statement} Prepared statement for linking atoms to tags
 */
export function prepareAtomTagInsert(db) {
  return db.prepare(`
    INSERT OR IGNORE INTO atom_tags (atom_id, tag_id)
    VALUES (?, ?)
  `);
}

/**
 * Check if an atom with the given source URL already exists
 * @param {Database} db - The database instance
 * @param {string} sourceUrl - The source URL to check
 * @returns {boolean} True if duplicate exists
 */
export function checkDuplicateBySourceUrl(db, sourceUrl) {
  const stmt = db.prepare('SELECT 1 FROM atoms WHERE source_url = ? LIMIT 1');
  return stmt.get(sourceUrl) !== undefined;
}

/**
 * Get existing tag by name (case-insensitive)
 * @param {Database} db - The database instance
 * @param {string} name - The tag name to find
 * @returns {Object|undefined} The tag row if found
 */
export function getTagByName(db, name) {
  const stmt = db.prepare('SELECT id, name, parent_id FROM tags WHERE LOWER(name) = LOWER(?) LIMIT 1');
  return stmt.get(name);
}

/**
 * Get or create a tag by name
 * @param {Database} db - The database instance
 * @param {string} name - The tag name
 * @param {string|null} parentId - Optional parent tag ID
 * @param {Statement} insertStmt - Prepared insert statement
 * @returns {Object} The tag object with id and isNew flag
 */
export function getOrCreateTag(db, name, parentId, insertStmt) {
  const existing = getTagByName(db, name);
  if (existing) {
    return { id: existing.id, name: existing.name, isNew: false };
  }

  const id = randomUUID();
  const now = new Date().toISOString();
  insertStmt.run(id, name, parentId, now);
  return { id, name, isNew: true };
}

/**
 * Parse command line arguments
 * @param {string[]} args - Process arguments (process.argv.slice(2))
 * @param {Object} defaults - Default values for options
 * @returns {Object} Parsed arguments
 */
export function parseArgs(args, defaults = {}) {
  const result = {
    positional: [],
    db: defaults.db || null,
    max: defaults.max || null,
    dryRun: defaults.dryRun || false,
    jsonOutput: defaults.jsonOutput || false,
    exclude: defaults.exclude || [],
    ...defaults,
  };

  for (let i = 0; i < args.length; i++) {
    const arg = args[i];

    if (arg === '--db' && args[i + 1]) {
      result.db = args[i + 1];
      i++;
    } else if (arg === '--max' && args[i + 1]) {
      result.max = parseInt(args[i + 1]);
      if (isNaN(result.max) || result.max <= 0) {
        console.error('\nError: --max must be a positive number');
        process.exit(1);
      }
      i++;
    } else if (arg === '--exclude' && args[i + 1]) {
      result.exclude.push(args[i + 1]);
      i++;
    } else if (arg === '--dry-run') {
      result.dryRun = true;
    } else if (arg === '--json-output') {
      result.jsonOutput = true;
    } else if (arg === '--help' || arg === '-h') {
      result.help = true;
    } else if (!arg.startsWith('--')) {
      result.positional.push(arg);
    }
  }

  return result;
}

/**
 * Print import summary
 * @param {Object} stats - Import statistics
 * @param {boolean} jsonOutput - Whether to output as JSON
 */
export function printSummary(stats, jsonOutput = false) {
  if (jsonOutput) {
    console.log(JSON.stringify(stats));
    return;
  }

  console.log('\n' + '='.repeat(60));
  console.log(`Import complete!`);
  console.log(`  Imported: ${stats.imported} notes`);
  if (stats.tagsCreated > 0) {
    console.log(`  Tags created: ${stats.tagsCreated}`);
  }
  if (stats.tagsLinked > 0) {
    console.log(`  Tags linked: ${stats.tagsLinked}`);
  }
  if (stats.skipped > 0) {
    console.log(`  Skipped: ${stats.skipped} (duplicates/empty)`);
  }
  if (stats.errors > 0) {
    console.log(`  Errors: ${stats.errors}`);
  }

  if (stats.imported > 0) {
    console.log('\nNext steps:');
    console.log('1. Start the Atomic app');
    console.log('2. Embeddings will process automatically in the background');
    console.log('3. Watch atoms update with tags as processing completes');
  }
}

/**
 * Generate a unique ID
 * @returns {string} UUID v4
 */
export function generateId() {
  return randomUUID();
}

/**
 * Get current ISO timestamp
 * @returns {string} ISO 8601 timestamp
 */
export function now() {
  return new Date().toISOString();
}

export default {
  getDefaultDbPath,
  openDatabase,
  prepareAtomInsert,
  prepareTagInsert,
  prepareAtomTagInsert,
  checkDuplicateBySourceUrl,
  getTagByName,
  getOrCreateTag,
  parseArgs,
  printSummary,
  generateId,
  now,
};
