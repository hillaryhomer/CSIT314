// Run the Python backend with a dedicated test database, not the user database.
import { mkdirSync } from 'node:fs';
import { randomUUID } from 'node:crypto';
import { resolve } from 'node:path';
import { spawn, spawnSync } from 'node:child_process';

mkdirSync('.test-data', { recursive: true });
const python = process.env.PYTHON || 'python';
// runpy also supports the embedded Python interpreter with an isolated import path.
const entry = "import runpy,sys;sys.path.insert(0,'.');sys.argv=['backend.app',*sys.argv[1:]];runpy.run_module('backend.app',run_name='__main__')";
const env = {
  ...process.env, APP_ENV: 'development',
  DATABASE_PATH: resolve('.test-data', `python-browser-${randomUUID()}.sqlite`),
  PORT: '4174', APP_ORIGIN: 'http://127.0.0.1:4174',
};
const seed = spawnSync(python, ['-c', entry, '--dev', '--seed'], { env, stdio: 'inherit' });
if (seed.error) throw seed.error;
if (seed.status !== 0) process.exit(seed.status || 1);
const server = spawn(python, ['-c', entry, '--dev', '--serve-ui'], { env, stdio: 'inherit' });
server.on('error', error => { console.error(error.message); process.exit(1); });
server.on('exit', code => process.exit(code || 0));
process.on('SIGINT', () => server.kill());
process.on('SIGTERM', () => server.kill());
