// scripts/build-release.js
import { execSync } from 'child_process';
import fs from 'fs';
import path from 'path';
import readline from 'readline';
import { fileURLToPath } from 'url';
import {
  getPreviousTag,
  generateChangelogBody,
  prependChangelog,
} from './generate-changelog.js';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const PROJECT_ROOT = path.resolve(__dirname, '..');
const TAURI_DIR = path.join(PROJECT_ROOT, 'src-tauri');

function log(msg) {
  console.log(msg);
}

function error(msg) {
  console.error(`ERROR: ${msg}`);
  process.exit(1);
}

function parseVersion(versionStr) {
  const match = versionStr.match(/^(\d+)\.(\d+)\.(\d+)$/);
  if (!match) return null;
  return {
    major: parseInt(match[1]),
    minor: parseInt(match[2]),
    patch: parseInt(match[3])
  };
}

function formatVersion(v) {
  return `${v.major}.${v.minor}.${v.patch}`;
}

function bumpVersion(versionStr, type) {
  const v = parseVersion(versionStr);
  if (!v) error(`Invalid version: ${versionStr}`);

  if (type === 'major') {
    v.major++;
    v.minor = 0;
    v.patch = 0;
  } else if (type === 'minor') {
    v.minor++;
    v.patch = 0;
  } else if (type === 'patch') {
    v.patch++;
  }

  return formatVersion(v);
}

function getCurrentVersion() {
  const configPath = path.join(TAURI_DIR, 'tauri.conf.json');
  const config = JSON.parse(fs.readFileSync(configPath, 'utf8'));
  return config.version;
}

function updateVersion(newVersion) {
  log(`Updating version to ${newVersion}...`);

  // Update tauri.conf.json
  const tauriConfigPath = path.join(TAURI_DIR, 'tauri.conf.json');
  const tauriConfig = JSON.parse(fs.readFileSync(tauriConfigPath, 'utf8'));
  tauriConfig.version = newVersion;
  fs.writeFileSync(tauriConfigPath, JSON.stringify(tauriConfig, null, 2) + '\n');

  // Update Cargo.toml
  const cargoTomlPath = path.join(TAURI_DIR, 'Cargo.toml');
  let cargoToml = fs.readFileSync(cargoTomlPath, 'utf8');
  cargoToml = cargoToml.replace(/^version = ".*"$/m, `version = "${newVersion}"`);
  fs.writeFileSync(cargoTomlPath, cargoToml);

  // Update package.json
  const packageJsonPath = path.join(PROJECT_ROOT, 'package.json');
  const packageJson = JSON.parse(fs.readFileSync(packageJsonPath, 'utf8'));
  packageJson.version = newVersion;
  fs.writeFileSync(packageJsonPath, JSON.stringify(packageJson, null, 2) + '\n');

  log(`Updated version in all files`);
}

function exec(cmd) {
  execSync(cmd, { cwd: PROJECT_ROOT, stdio: 'inherit' });
}

function execCapture(cmd) {
  return execSync(cmd, { cwd: PROJECT_ROOT, encoding: 'utf8' }).trim();
}

function askConfirmation(question) {
  const rl = readline.createInterface({
    input: process.stdin,
    output: process.stdout,
  });
  return new Promise((resolve) => {
    rl.question(question, (answer) => {
      rl.close();
      resolve(answer.trim().toLowerCase());
    });
  });
}

// Files this script touches before the release commit. If the user aborts at
// the confirmation prompt, we roll these back so the working tree is clean
// and the next `npm run release:*` invocation can run fresh.
const RELEASE_FILES = [
  'package.json',
  'package-lock.json',
  'src-tauri/tauri.conf.json',
  'src-tauri/Cargo.toml',
  'Cargo.lock',
];

function revertReleaseChanges(changelogExisted) {
  log('\nReverting uncommitted release changes...');
  try {
    exec(`git checkout -- ${RELEASE_FILES.join(' ')}`);
  } catch (err) {
    console.error(`  (failed to restore release files: ${err?.message || err})`);
  }
  const changelogPath = path.join(PROJECT_ROOT, 'CHANGELOG.md');
  if (changelogExisted) {
    try {
      exec('git checkout -- CHANGELOG.md');
    } catch (err) {
      console.error(`  (failed to restore CHANGELOG.md: ${err?.message || err})`);
    }
  } else if (fs.existsSync(changelogPath)) {
    try {
      fs.unlinkSync(changelogPath);
    } catch (err) {
      console.error(`  (failed to delete CHANGELOG.md: ${err?.message || err})`);
    }
  }
}

function preflight() {
  log('Running preflight checks...');

  // Must be on main branch
  const branch = execCapture('git rev-parse --abbrev-ref HEAD');
  if (branch !== 'main') {
    error(`Must be on 'main' branch to release (currently on '${branch}')`);
  }

  // Working tree must be clean
  const status = execCapture('git status --porcelain');
  if (status) {
    error(`Working tree is not clean. Commit or stash changes first:\n${status}`);
  }

  // Pull latest from origin/main (fast-forward only — fails on divergence)
  log('Pulling latest from origin/main...');
  exec('git pull --ff-only origin main');
}

function showHelp() {
  console.log(`
Usage: node scripts/build-release.js <bump-type>

Bump version, commit, tag, and push to trigger GitHub Actions release build.

Arguments:
  patch    Bump patch version (0.2.0 -> 0.2.1)
  minor    Bump minor version (0.2.0 -> 0.3.0)
  major    Bump major version (0.2.0 -> 1.0.0)

Examples:
  npm run release:patch
  npm run release:minor
  npm run release:major
  `);
}

async function main() {
  const bumpType = process.argv[2];

  if (!bumpType || bumpType === '--help' || bumpType === '-h') {
    showHelp();
    process.exit(bumpType ? 0 : 1);
  }

  if (!['patch', 'minor', 'major'].includes(bumpType)) {
    error(`Invalid bump type: ${bumpType}. Use patch, minor, or major.`);
  }

  preflight();

  // Capture the previous release tag *before* we create the new one. This is
  // the range the AI changelog summariser will walk.
  const previousTag = getPreviousTag();

  // Get current version and bump it
  const currentVersion = getCurrentVersion();
  const newVersion = bumpVersion(currentVersion, bumpType);
  const tagName = `v${newVersion}`;

  log(`\nReleasing ${tagName} (${currentVersion} -> ${newVersion})\n`);

  // Update version in all files
  updateVersion(newVersion);

  // Sync lockfiles so the bumped versions land in Cargo.lock and package-lock.json.
  // Without this, the next local build rewrites them and leaves stale state in git.
  log('\nSyncing lockfiles...');
  exec('cargo update --workspace --offline');
  exec('npm install --package-lock-only --silent');

  // Generate the AI changelog entry before committing so CHANGELOG.md lands in
  // the same commit as the version bump. If the SDK call fails we abort here,
  // before anything is committed or pushed.
  const changelogPath = path.join(PROJECT_ROOT, 'CHANGELOG.md');
  const changelogExisted = fs.existsSync(changelogPath);

  log(`\nGenerating changelog entry${previousTag ? ` since ${previousTag}` : ''} via Claude Agent SDK...`);
  const changelogBody = await generateChangelogBody(previousTag, newVersion);
  log(`\n--- Changelog entry ---\n${changelogBody}\n-----------------------\n`);
  prependChangelog(newVersion, changelogBody);
  log(`Updated ${path.relative(PROJECT_ROOT, changelogPath)}`);

  // Wait for explicit confirmation before cutting the release. The user can
  // open CHANGELOG.md in their editor, tweak the entry, save, then confirm —
  // whatever's on disk at confirmation time is what gets committed.
  const sigintHandler = () => {
    revertReleaseChanges(changelogExisted);
    process.exit(130);
  };
  process.on('SIGINT', sigintHandler);

  log('\nReview CHANGELOG.md above (or open it in your editor to tweak).');
  const answer = await askConfirmation(`Proceed with release ${tagName}? [Y/n] `);
  process.off('SIGINT', sigintHandler);

  if (answer === 'n' || answer === 'no') {
    revertReleaseChanges(changelogExisted);
    log('\nAborted by user. No commit, tag, or push.');
    process.exit(0);
  }

  // Commit, tag, and push
  log('\nCommitting version bump...');
  exec('git add package.json package-lock.json src-tauri/tauri.conf.json src-tauri/Cargo.toml Cargo.lock CHANGELOG.md');
  exec(`git commit -m "Bump version to ${tagName}"`);

  log(`\nCreating tag ${tagName}...`);
  exec(`git tag -a ${tagName} -m "Release ${tagName}"`);

  log('\nPushing to origin...');
  exec('git push && git push --tags');

  log(`\nDone! GitHub Actions will now build and release ${tagName}`);
  log('Watch progress at: https://github.com/kenforthewin/atomic/actions');
}

main().catch((err) => {
  error(err?.stack || err?.message || String(err));
});
