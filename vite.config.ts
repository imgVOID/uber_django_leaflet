// vite.config.ts
import { defineConfig } from 'vite';
import { fileURLToPath } from 'url';
import { dirname, resolve } from 'path';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

export default defineConfig({
  base: '/static/', // Установите '/static/' вместо '/'
  build: {
    outDir: 'static/dist',
    manifest: true,
    rollupOptions: {
      input: {
        taxi_request: resolve(__dirname, 'assets/taxi_request.ts'),
        taxi_map: resolve(__dirname, 'assets/taxi_map.ts'),
      },
    },
  },
  server: {
    origin: 'http://localhost:5173', 
    host: 'localhost',
    port: 5173,
    cors: true,
    hmr: {
      host: 'localhost',
      port: 5173,
    },
  },
});