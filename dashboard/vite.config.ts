import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    // Mirrors the same-origin /api/* proxy Azure Static Web Apps provides
    // in production for a linked Function App backend.
    proxy: {
      '/api': 'http://localhost:7071',
    },
  },
})
