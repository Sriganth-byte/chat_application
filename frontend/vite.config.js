import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import mkcert from 'vite-plugin-mkcert'

export default defineConfig({
  plugins: [
    react(),
    // Generates a locally-trusted CA cert that includes the LAN IP.
    // allowH2: false — forces HTTP/1.1 over TLS.
    // HTTP/2 (the mkcert v2 default) breaks Vite's middleware which sets
    // res.statusMessage, a field that RFC7540 §8.1.2.4 explicitly forbids,
    // causing 504 errors on every /.vite/deps/* pre-bundled module.
    mkcert({ allowH2: false }),
  ],
  server: {
    host: true,        // bind to 0.0.0.0 — accessible over LAN
    port: 3000,
    strictPort: true,
    // https is managed by the mkcert plugin above — don't set it here
    // to avoid creating a conflicting second TLS context.
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
        secure: false,
      },
      '/ws': {
        target: 'ws://127.0.0.1:8000',
        ws: true,
        changeOrigin: true,
        secure: false,
      },
      // Proxy media/static files so LAN devices can load images, audio, and
      // video that Django saved locally. Without this proxy, build_absolute_uri
      // returns http://127.0.0.1:8000/media/... which only works on the server
      // machine — other devices get a connection-refused error.
      '/media': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
        secure: false,
      },
      '/static': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
        secure: false,
      },
    },
  },
})

