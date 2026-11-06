// Run the Python backend with a dedicated test database, not the user database.
import { mkdirSync } from 'node:fs';
import { randomUUID } from 'node:crypto';
import { resolve } from 'node:path';
import { spawn, spawnSync } from 'node:child_process';

mkdirSync('.test-data', { recursive: true });
const python = process.env.PYTHON || 'python';
const member2 = process.env.MEMBER2_BROWSER === '1';
const port = process.env.BROWSER_TEST_PORT || (member2 ? '4175' : '4174');
let stopping = false;
// runpy also supports the embedded Python interpreter with an isolated import path.
const entry = "import runpy,sys;sys.path.insert(0,'.');sys.argv=['backend.app',*sys.argv[1:]];runpy.run_module('backend.app',run_name='__main__')";
const env = {
  ...process.env, APP_ENV: 'development',
  DATABASE_PATH: resolve('.test-data', `python-browser-${randomUUID()}.sqlite`),
  PORT: port, APP_ORIGIN: `http://127.0.0.1:${port}`,
};
const seed = spawnSync(python, ['-c', entry, '--dev', '--seed'], { env, stdio: 'inherit' });
if (seed.error) throw seed.error;
if (seed.status !== 0) process.exit(seed.status || 1);
if (member2) {
  const fixture = spawnSync(python, ['-c', "import sys,runpy;sys.path.insert(0,'.');runpy.run_path('tests/browser_fixture.py')"], { env, stdio: 'inherit' });
  if (fixture.error) throw fixture.error;
  if (fixture.status !== 0) process.exit(fixture.status || 1);
}
const server = spawn(python, ['-c', entry, ...(member2 ? [] : ['--dev']), '--serve-ui'], { env, stdio: 'inherit' });
server.on('error', error => { console.error(error.message); process.exit(1); });
server.on('exit', code => process.exit(stopping ? 0 : code || 0));
const stop = () => { stopping = true; server.kill(); };
process.on('message', message => { if (message === 'shutdown') stop(); });
process.on('disconnect', stop);
process.on('SIGINT', stop);
process.on('SIGTERM', stop);
