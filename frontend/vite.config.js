import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// El frontend (5173) le habla al backend FastAPI (8000) a través de este proxy.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': 'http://127.0.0.1:8000',
      '/static': 'http://127.0.0.1:8000',
    },
  },
})
