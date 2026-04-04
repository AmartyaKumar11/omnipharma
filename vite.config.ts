import path from "node:path";
import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  server: {
    port: 5173,
    strictPort: true,
    // Dual-stack (IPv4 + IPv6) so http://localhost:5173 resolves to ::1 and still hits Vite on Windows.
    host: "::",
    // Prefer opening IPv4 in the default browser to avoid stale tabs on the wrong host.
    open: "http://127.0.0.1:5173/",
    proxy: {
      "/api": {
        // Use :8020 + uvicorn --app-dir so the API always loads d:\\centific\\backend (not a stale OneDrive copy).
        target: "http://127.0.0.1:8020",
        changeOrigin: true,
        rewrite: (p) => p.replace(/^\/api/, ""),
      },
    },
  },
});
