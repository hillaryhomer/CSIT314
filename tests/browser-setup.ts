// Own the server directly: Windows-restricted environments may block taskkill /T.
// IPC asks the harness to stop its own Python child without process enumeration.
import { spawn } from 'node:child_process';
import type { FullConfig } from '@playwright/test';

export default async function setup(config: FullConfig) {
  const baseURL = String(config.projects[0].use.baseURL);
  const port = new URL(baseURL).port;
  const member2 = port !== '4174';
  const existing = await fetch(baseURL + '/api/health', { signal: AbortSignal.timeout(500) }).catch(() => null);
  if (existing) throw new Error(`${baseURL} is already in use.`);
  const child = spawn(process.execPath, ['tests/browser-server.mjs'], {
    env: { ...process.env, MEMBER2_BROWSER: member2 ? '1' : '0', BROWSER_TEST_PORT: port },
    stdio: ['ignore', 'pipe', 'pipe', 'ipc'], windowsHide: true,
  });
  let log = '', launchError: Error | null = null;
  child.on('error', error => { launchError = error; });
  for (const output of [child.stdout, child.stderr]) output?.on('data', chunk => { log = (log + chunk.toString()).slice(-8000); });
  const exited = new Promise<void>(resolve => child.once('exit', () => resolve()));
  async function stop() {
    if (child.exitCode !== null || child.signalCode !== null) return;
    if (child.connected) child.send('shutdown');
    let timer: ReturnType<typeof setTimeout>;
    await Promise.race([exited, new Promise<void>(resolve => { timer = setTimeout(() => { child.kill(); resolve(); }, 5000); })]);
    clearTimeout(timer!);
  }
  try {
    const deadline = Date.now() + 30_000;
    while (Date.now() < deadline) {
      if (launchError || child.exitCode !== null) throw launchError ?? new Error(log);
      const response = await fetch(baseURL + '/api/health', { signal: AbortSignal.timeout(500) }).catch(() => null);
      if (response?.ok) return stop;
      await new Promise(resolve => setTimeout(resolve, 200));
    }
    throw new Error('Browser server did not become ready. ' + log);
  } catch (error) { await stop(); throw error; }
}
