import { defineConfig } from 'vite';
import { svelte } from '@sveltejs/vite-plugin-svelte';

const backend = 'http://127.0.0.1:28347';
const port = 43179;
const frontend = `http://127.0.0.1:${port}`;

/** Command. Forward only this development origin as the backend origin.
 * @param {object} outgoing Proxy request. @param {object} incoming Browser request.
 * @returns {void} Other origins remain unchanged and are rejected by the backend.
 */
function forwardOrigin(outgoing, incoming) {
  if (incoming.headers.origin === frontend) outgoing.setHeader('origin', backend);
}

/** Command. Install HTTP and WebSocket origin forwarding on the proxy.
 * @param {object} proxy Vite proxy. @returns {void}
 */
function configure(proxy) {
  proxy.on('proxyReq', forwardOrigin);
  proxy.on('proxyReqWs', forwardOrigin);
}

export default defineConfig({ plugins: [svelte()], server: {
  host: '127.0.0.1', port, strictPort: true,
  proxy: {
    '/api': { target: backend, changeOrigin: true, configure },
    '/ws': { target: backend, changeOrigin: true, ws: true, configure },
  },
} });
