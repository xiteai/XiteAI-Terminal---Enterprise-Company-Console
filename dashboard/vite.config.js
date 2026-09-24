import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Dev: `npm run dev` serves the UI on :5173 and forwards /api to the Python
// server on :8710. Build: `npm run build` writes dist/, which the Python
// server serves itself (no Node needed in production).
//
// Every build gets an id, written into index.html and compiled into the app,
// so a page left open can tell the server has newer screens (UpdateNotice.jsx).
const UI_BUILD = Date.now().toString(36);

export default defineConfig({
  plugins: [
    react(),
    {
      name: "ui-build-id",
      transformIndexHtml: () => [{ tag: "meta", attrs: { name: "ui-build", content: UI_BUILD }, injectTo: "head" }],
    },
  ],
  define: { __UI_BUILD__: JSON.stringify(UI_BUILD) },
  server: {
    port: 5173,
    proxy: { "/api": "http://127.0.0.1:8710" },
  },
  build: {
    outDir: "dist",
    emptyOutDir: true,
    sourcemap: false,
    chunkSizeWarningLimit: 900,
  },
});
