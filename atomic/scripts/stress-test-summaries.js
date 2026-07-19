// scripts/stress-test-summaries.js
// Fast stress test: fetches Wikipedia summaries (short extracts) for volume testing.
// Uses the summary API (~1-2 paragraphs per article) instead of full HTML.
// Crawls links aggressively to reach thousands of articles quickly.
//
// Usage:
//   node scripts/stress-test-summaries.js --token <token> --count 1000
//   node scripts/stress-test-summaries.js --token <token> --count 5000 --skip-monitor

function parseArgs() {
  const args = process.argv.slice(2);
  const opts = {
    server: process.env.ATOMIC_SERVER || 'http://127.0.0.1:8080',
    token: process.env.ATOMIC_TOKEN || null,
    count: 1000,
    batchSize: 200,
    dbName: null, // null = use active db
    skipCreateDb: false,
    skipMonitor: false,
    timeout: 1800,
    concurrency: 10,
  };

  for (let i = 0; i < args.length; i++) {
    switch (args[i]) {
      case '--server': opts.server = args[++i]; break;
      case '--token': opts.token = args[++i]; break;
      case '--count': opts.count = parseInt(args[++i], 10); break;
      case '--batch-size': opts.batchSize = parseInt(args[++i], 10); break;
      case '--db-name': opts.dbName = args[++i]; break;
      case '--skip-create-db': opts.skipCreateDb = true; break;
      case '--skip-monitor': opts.skipMonitor = true; break;
      case '--timeout': opts.timeout = parseInt(args[++i], 10); break;
      case '--help':
        console.log(`Usage: node scripts/stress-test-summaries.js [options]

Options:
  --server <url>       Server URL (default: http://127.0.0.1:8080)
  --token <token>      API token (required, or ATOMIC_TOKEN env)
  --count <n>          Number of articles (default: 1000)
  --batch-size <n>     Atoms per bulk API call (default: 200)
  --db-name <name>     Create a new database with this name
  --skip-create-db     Use active database
  --skip-monitor       Don't wait for embedding pipeline
  --timeout <s>        Pipeline timeout in seconds (default: 1800)`);
        process.exit(0);
    }
  }

  if (!opts.token) {
    console.error('Error: --token required (or set ATOMIC_TOKEN env)');
    process.exit(1);
  }
  return opts;
}

const sleep = (ms) => new Promise(r => setTimeout(r, ms));

function createClient(serverUrl, token, dbId) {
  const base = serverUrl.replace(/\/$/, '');
  return async function request(method, path, body) {
    const headers = {
      Authorization: `Bearer ${token}`,
      'Content-Type': 'application/json',
    };
    if (dbId) headers['X-Atomic-Database'] = dbId;
    const res = await fetch(`${base}${path}`, {
      method, headers,
      body: body != null ? JSON.stringify(body) : undefined,
    });
    if (!res.ok) {
      const text = await res.text().catch(() => '');
      throw new Error(`${method} ${path} → ${res.status}: ${text}`);
    }
    return res.json();
  };
}

// --- Wikipedia Summary API ---

// Broad seed categories for diverse content
const SEEDS = [
  // Science
  'Physics', 'Chemistry', 'Biology', 'Mathematics', 'Astronomy', 'Geology', 'Ecology',
  'Quantum_mechanics', 'Evolution', 'Genetics', 'Neuroscience', 'Climate_change',
  // Technology
  'Computer_science', 'Artificial_intelligence', 'Machine_learning', 'Internet',
  'Blockchain', 'Robotics', 'Nanotechnology', 'Space_exploration', 'Nuclear_energy',
  // History
  'Ancient_Egypt', 'Roman_Empire', 'Medieval_Europe', 'Renaissance', 'Industrial_Revolution',
  'World_War_I', 'World_War_II', 'Cold_War', 'French_Revolution', 'American_Revolution',
  // Philosophy
  'Philosophy', 'Ethics', 'Epistemology', 'Existentialism', 'Stoicism', 'Buddhism',
  'Confucianism', 'Utilitarianism', 'Pragmatism', 'Phenomenology',
  // Arts
  'Literature', 'Classical_music', 'Jazz', 'Impressionism', 'Surrealism', 'Architecture',
  'Film', 'Photography', 'Dance', 'Theatre',
  // Geography
  'Pacific_Ocean', 'Amazon_rainforest', 'Sahara', 'Himalayas', 'Great_Barrier_Reef',
  'Antarctica', 'Mediterranean_Sea', 'Nile', 'Alps', 'Grand_Canyon',
  // People
  'Albert_Einstein', 'Marie_Curie', 'Leonardo_da_Vinci', 'William_Shakespeare',
  'Nikola_Tesla', 'Ada_Lovelace', 'Charles_Darwin', 'Isaac_Newton',
  // Society
  'Democracy', 'Capitalism', 'Socialism', 'Human_rights', 'Globalization',
  'United_Nations', 'European_Union', 'Urbanization', 'Education', 'Public_health',
];

async function fetchSummary(title) {
  try {
    const url = `https://en.wikipedia.org/api/rest_v1/page/summary/${encodeURIComponent(title)}`;
    const res = await fetch(url, {
      headers: { 'User-Agent': 'AtomicStressTest/1.0' },
    });
    if (!res.ok) return null;
    const data = await res.json();
    if (data.type === 'disambiguation' || data.type === 'no-extract') return null;
    const extract = data.extract?.trim();
    if (!extract || extract.length < 50) return null;
    return {
      title: data.title || title.replace(/_/g, ' '),
      content: `# ${data.title || title.replace(/_/g, ' ')}\n\n${extract}`,
      url: data.content_urls?.desktop?.page || `https://en.wikipedia.org/wiki/${encodeURIComponent(title)}`,
    };
  } catch {
    return null;
  }
}

async function fetchLinks(title, limit = 30) {
  try {
    const res = await fetch(
      `https://en.wikipedia.org/w/api.php?action=query&titles=${encodeURIComponent(title)}&prop=links&pllimit=${limit}&plnamespace=0&format=json&origin=*`,
      { headers: { 'User-Agent': 'AtomicStressTest/1.0' } }
    );
    if (!res.ok) return [];
    const data = await res.json();
    const pages = data.query?.pages;
    if (!pages) return [];
    const pageId = Object.keys(pages)[0];
    return (pages[pageId]?.links || []).map(l => l.title.replace(/ /g, '_'));
  } catch {
    return [];
  }
}

async function fetchArticles(count, concurrency) {
  const articles = [];
  const seen = new Set();
  const queue = [...SEEDS];
  const startTime = Date.now();

  // Process queue with concurrency
  async function processOne() {
    while (articles.length < count && queue.length > 0) {
      const title = queue.shift();
      if (!title || seen.has(title)) continue;
      seen.add(title);

      const article = await fetchSummary(title);
      if (article) {
        articles.push(article);
        if (articles.length % 50 === 0 || articles.length === count) {
          process.stdout.write(`\r  Fetched ${articles.length}/${count} summaries (queue: ${queue.length})`);
        }
      }

      // Expand links to keep the queue full
      if (queue.length < count * 2) {
        const links = await fetchLinks(title, 30);
        for (const link of links) {
          if (!seen.has(link)) queue.push(link);
        }
      }

      // Light rate limit
      await sleep(20);
    }
  }

  // Run concurrent workers
  const workers = [];
  for (let i = 0; i < concurrency; i++) {
    workers.push(processOne());
  }
  await Promise.all(workers);

  process.stdout.write('\n');
  return { articles: articles.slice(0, count), fetchTime: (Date.now() - startTime) / 1000 };
}

// --- Pipeline tracker (simplified) ---

class PipelineTracker {
  constructor(atomIds) {
    this.pending = new Set(atomIds);
    this.done = 0;
    this.total = atomIds.length;
    this._resolve = null;
    this._interval = null;
  }

  handleEvent(event) {
    const { type, atom_id } = event;
    if (!atom_id || !this.pending.has(atom_id)) return;
    // Consider done when tagged (tagging happens after embedding)
    if (type === 'TaggingComplete' || type === 'TaggingFailed' || type === 'TaggingSkipped') {
      this.pending.delete(atom_id);
      this.done++;
      if (this._resolve && this.pending.size === 0) this._resolve();
    }
  }

  waitForCompletion(timeoutMs) {
    if (this.pending.size === 0) return Promise.resolve();
    return new Promise(resolve => {
      this._resolve = resolve;
      this._interval = setInterval(() => {
        process.stdout.write(`\r  Pipeline: ${this.done}/${this.total} complete`);
      }, 5000);
      setTimeout(() => {
        clearInterval(this._interval);
        resolve();
      }, timeoutMs);
    });
  }

  cleanup() {
    if (this._interval) clearInterval(this._interval);
  }
}

// --- Main ---

async function main() {
  const opts = parseArgs();

  console.log(`Atomic Summary Stress Test`);
  console.log(`  Server:  ${opts.server}`);
  console.log(`  Count:   ${opts.count}`);
  console.log(`  Batch:   ${opts.batchSize}`);
  console.log('');

  const api = createClient(opts.server, opts.token, null);
  let dbList;
  try {
    dbList = await api('GET', '/api/databases');
    console.log(`Connected (${dbList.databases.length} databases)`);
  } catch (err) {
    console.error(`Connection failed: ${err.message}`);
    process.exit(1);
  }

  let dbId = null;
  if (opts.dbName) {
    const db = await api('POST', '/api/databases', { name: opts.dbName });
    dbId = db.id;
    console.log(`Created database: ${opts.dbName} (${dbId})`);
  } else if (opts.skipCreateDb || !opts.dbName) {
    dbId = dbList.active_id;
    const active = dbList.databases.find(d => d.id === dbId);
    console.log(`Using active database: ${active?.name || dbId}`);
  }

  const dbApi = createClient(opts.server, opts.token, dbId);

  // WebSocket for monitoring
  let ws = null;
  if (!opts.skipMonitor) {
    const wsUrl = opts.server.replace(/^http/, 'ws') + `/ws?token=${opts.token}`;
    ws = new WebSocket(wsUrl);
    await new Promise((resolve, reject) => {
      ws.onopen = resolve;
      ws.onerror = () => reject(new Error('WebSocket failed'));
      setTimeout(() => reject(new Error('WebSocket timeout')), 10000);
    });
    console.log('WebSocket connected');
  }

  // Fetch summaries
  console.log(`\nFetching ${opts.count} Wikipedia summaries...`);
  const { articles, fetchTime } = await fetchArticles(opts.count, opts.concurrency);
  console.log(`Fetched ${articles.length} in ${fetchTime.toFixed(1)}s (${(articles.length / fetchTime).toFixed(0)}/sec)`);

  if (articles.length === 0) {
    console.error('No articles fetched');
    ws?.close();
    process.exit(1);
  }

  // Import in batches
  console.log(`\nImporting ${articles.length} atoms...`);
  const importStart = Date.now();
  const allAtomIds = [];

  for (let i = 0; i < articles.length; i += opts.batchSize) {
    const batch = articles.slice(i, i + opts.batchSize);
    const payload = batch.map(a => ({ content: a.content, source_url: a.url }));

    try {
      const result = await dbApi('POST', '/api/atoms/bulk', payload);
      for (const atom of result.atoms) allAtomIds.push(atom.id);
      console.log(`  Batch ${Math.floor(i / opts.batchSize) + 1}: ${result.count} imported`);
    } catch (err) {
      // Split on payload too large
      if (err.message.includes('413') && batch.length > 1) {
        const mid = Math.ceil(batch.length / 2);
        for (const half of [batch.slice(0, mid), batch.slice(mid)]) {
          try {
            const result = await dbApi('POST', '/api/atoms/bulk', half.map(a => ({ content: a.content, source_url: a.url })));
            for (const atom of result.atoms) allAtomIds.push(atom.id);
          } catch (e2) {
            console.error(`  Batch failed: ${e2.message}`);
          }
        }
      } else {
        console.error(`  Batch failed: ${err.message}`);
      }
    }
  }

  const importTime = (Date.now() - importStart) / 1000;
  console.log(`Imported ${allAtomIds.length} atoms in ${importTime.toFixed(1)}s`);

  // Monitor pipeline
  if (!opts.skipMonitor && ws && allAtomIds.length > 0) {
    console.log(`\nMonitoring pipeline (timeout: ${opts.timeout}s)...`);
    const tracker = new PipelineTracker(allAtomIds);
    ws.onmessage = (event) => {
      try { tracker.handleEvent(JSON.parse(event.data)); } catch {}
    };
    await tracker.waitForCompletion(opts.timeout * 1000);
    tracker.cleanup();
    console.log(`\nPipeline: ${tracker.done}/${tracker.total} complete`);
    ws.close();
  } else {
    ws?.close();
  }

  console.log('\nDone!');
}

main().catch(err => {
  console.error(err);
  process.exit(1);
});
