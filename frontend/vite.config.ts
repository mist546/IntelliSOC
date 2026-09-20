import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    // Bind IPv4 explicitly: Windows resolves "localhost" to both ::1 and
    // 127.0.0.1, and browsers often prefer IPv6 - the default host binding
    // only listens on IPv6, making the dev server unreachable from a browser
    // navigating to 127.0.0.1 (and VITE_API_BASE_URL is pinned to
    // 127.0.0.1 to avoid the same issue on the backend side).
    host: '127.0.0.1',
    port: 5173,
  },
})
