import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

const backendUrl = process.env.VITE_BACKEND_URL || 'http://backend:8000'

export default defineConfig({
  plugins: [vue()],
  server: {
    host: '0.0.0.0',
    port: 4200,
    proxy: {
      '/api': {
        target: backendUrl,
        changeOrigin: true,
        timeout: 300000,
      },
      '/ws': {
        target: backendUrl.replace('http', 'ws'),
        ws: true,
      },
    },
  },
})
