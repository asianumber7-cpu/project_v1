// frontend/vite.config.js (★ terser 대신 esbuild 사용 ★)

import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    host: '0.0.0.0',
    port: 5174,
    watch: {
      usePolling: true
    }
  },
  build: {
    outDir: 'dist',
    sourcemap: false,
    minify: 'esbuild',  // ← terser 대신 esbuild 사용 (더 빠름)
    chunkSizeWarningLimit: 1000
  }
})