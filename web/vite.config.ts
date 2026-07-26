import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  build: {
    // react-snap prerenders with an old bundled Chromium (puppeteer 1.20.0)
    // that can't parse optional chaining / nullish coalescing. Emitting ES2019
    // strips `?.`/`??` so the app runs there and the landing prerenders.
    target: "es2019",
  },
  server: {
    port: 5173,
  },
});

