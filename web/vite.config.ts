import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    host: "0.0.0.0",
    allowedHosts: "all",
    proxy: {
      "/v1": { target: "http://api:8000", changeOrigin: true },
      "/auth": { target: "http://api:8000", changeOrigin: true },
      "/healthz": { target: "http://api:8000", changeOrigin: true },
    },
  },
});
