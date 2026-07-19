#!/usr/bin/env node

import { spawnSync } from 'node:child_process';

const url = process.env.ATOMIC_MCP_URL ?? process.argv[2];
const token = process.env.ATOMIC_API_TOKEN ?? process.argv[3];

if (!url || !token) {
  console.error(
    [
      'Usage:',
      '  ATOMIC_MCP_URL=http://localhost:8080/mcp ATOMIC_API_TOKEN=<token> npm run test:mcp-inspector',
      '  npm run test:mcp-inspector -- http://localhost:8080/mcp <token>',
      '',
      'This check expects an Atomic server to already be running.',
    ].join('\n'),
  );
  process.exit(2);
}

const result = spawnSync(
  'npx',
  [
    '-y',
    '@modelcontextprotocol/inspector',
    '--cli',
    url,
    '--transport',
    'http',
    '--method',
    'tools/list',
    '--header',
    `Authorization: Bearer ${token}`,
  ],
  {
    stdio: 'inherit',
    env: {
      ...process.env,
      MCP_AUTO_OPEN_ENABLED: 'false',
    },
  },
);

if (result.error) {
  console.error(result.error.message);
  process.exit(1);
}

process.exit(result.status ?? 1);
