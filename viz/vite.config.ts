import { defineConfig } from 'vite'

// base './' so `vite build` output can be opened from file:// and published as a
// self-contained artifact, not only served from a domain root.
export default defineConfig({
  base: './',
  build: {
    outDir: 'dist',
    assetsInlineLimit: 0,
  },
  server: { port: 5178, open: false },
  preview: { port: 4178, open: false },
})
