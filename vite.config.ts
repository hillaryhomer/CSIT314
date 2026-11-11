import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import { spawn } from 'child_process';
import fs from 'fs';
import path from 'path';

function autoBackendPlugin() {
  return {
    name: 'auto-backend',
    configureServer(server) {
      const venvPy = path.resolve('.venv', 'Scripts', 'python.exe');
      const py = fs.existsSync(venvPy) ? venvPy : 'python';
      console.log('\n[Vite] Starting Python backend server via', py, '...\n');
      const backend = spawn(py, ['app.py'], { stdio: 'inherit' });

      backend.on('error', (err) => {
        console.error('[Vite] Failed to start backend:', err);
      });

      const killBackend = () => {
        try { backend.kill(); } catch {}
      };
      process.on('exit', killBackend);
      process.on('SIGINT', () => { killBackend(); process.exit(); });
      process.on('SIGTERM', () => { killBackend(); process.exit(); });
    },
  };
}

export default defineConfig({
  plugins: [react(), autoBackendPlugin()],
  base: '/',
  server: {
    host: '127.0.0.1',
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:3002',
        changeOrigin: true,
      },
    },
  },
});
