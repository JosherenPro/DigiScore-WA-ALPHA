import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    // Sans host explicite, Vite n'ecoute que sur [::1] : http://127.0.0.1:5173
    // tombe alors en connexion refusee, et le tel de demo ne voit rien.
    host: true,
    port: 5173,
    proxy: {
      "/api": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
        rewrite: (p) => p.replace(/^\/api/, ""),
      },
    },
  },
});
