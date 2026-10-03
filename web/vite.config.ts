import { defineConfig, loadEnv, type Plugin } from "vite";
import react from "@vitejs/plugin-react";
import { VitePWA } from "vite-plugin-pwa";

const APP_DESCRIPTION =
  "Verifiko is an explainable verification workspace for evidence-driven risk assessment.";

// iOS reads these from <head>, not from the manifest. Only emitted when the PWA is
// enabled, so a flag-off build serves exactly the same <head> as before.
function appleWebAppTags(): Plugin {
  return {
    name: "verifiko-apple-web-app-tags",
    transformIndexHtml() {
      return [
        { tag: "link", attrs: { rel: "apple-touch-icon", href: "/apple-touch-icon-180x180.png" }, injectTo: "head" },
        { tag: "meta", attrs: { name: "apple-mobile-web-app-capable", content: "yes" }, injectTo: "head" },
        { tag: "meta", attrs: { name: "apple-mobile-web-app-status-bar-style", content: "black-translucent" }, injectTo: "head" },
        { tag: "meta", attrs: { name: "apple-mobile-web-app-title", content: "Verifiko" }, injectTo: "head" },
      ];
    },
  };
}

export default defineConfig(({ mode, isSsrBuild }) => {
  // VITE_PWA_ENABLED (build-time, off by default) turns on the installable PWA:
  // manifest + iOS tags + a service worker that precaches the app shell, registered
  // from src/pwa/registerPwa.ts.
  //
  // When it is off, the build still emits /sw.js, but as a self-destroying worker
  // that nothing registers. Browsers that never had the PWA ignore it; browsers that
  // installed it while the flag was on pick it up on their next update check, and it
  // unregisters itself and deletes its caches. Turning the flag off is the rollback.
  const pwaEnabled = loadEnv(mode, process.cwd(), "VITE_").VITE_PWA_ENABLED === "true";

  return {
    plugins: [
      react(),
      // The SSR build (scripts/prerender.mjs input) must not emit a service worker.
      ...(isSsrBuild
        ? []
        : [
            VitePWA({
              selfDestroying: !pwaEnabled,
              // Registered from the bundle, never as an inline script: the site's CSP
              // (vercel.json) has no 'unsafe-inline' in script-src.
              injectRegister: false,
              // The user confirms updates ("New version available · Reload"), so a new
              // worker never swaps the shell under a running page; old lazy chunks
              // keep resolving and lazyWithReload/RouteErrorBoundary stay in charge.
              registerType: "prompt",
              includeAssets: ["favicon.svg", "apple-touch-icon-180x180.png"],
              manifest: pwaEnabled
                ? {
                    name: "Verifiko",
                    short_name: "Verifiko",
                    description: APP_DESCRIPTION,
                    start_url: "/app",
                    scope: "/",
                    display: "standalone",
                    theme_color: "#0C1A2E",
                    background_color: "#0a0f1e",
                    lang: "en",
                    dir: "ltr",
                    icons: [
                      { src: "/pwa-192x192.png", sizes: "192x192", type: "image/png" },
                      { src: "/pwa-512x512.png", sizes: "512x512", type: "image/png" },
                      {
                        src: "/pwa-maskable-512x512.png",
                        sizes: "512x512",
                        type: "image/png",
                        purpose: "maskable",
                      },
                    ],
                  }
                : false,
              workbox: {
                // Precache only the static shell emitted by this build.
                globPatterns: ["**/*.{js,css,html,svg,png,webmanifest}"],
                cleanupOutdatedCaches: true,
                // SPA routing offline: navigations get the precached shell...
                navigateFallback: "/index.html",
                // ...except API-looking paths and real files (robots.txt, sitemap.xml).
                navigateFallbackDenylist: [/^\/api(\/|$)/, /\/[^/?]+\.[^/]+$/],
                // Deliberately no runtimeCaching: the API (api.verifiko.es), Google
                // Sign-In (accounts.google.com) and analytics are cross-origin and
                // always go to the network. Nothing dynamic is ever cached.
                runtimeCaching: [],
              },
            }),
            ...(pwaEnabled ? [appleWebAppTags()] : []),
          ]),
    ],
    define: {
      __PWA_ENABLED__: JSON.stringify(pwaEnabled),
    },
    build: {
      // react-snap prerenders with an old bundled Chromium (puppeteer 1.20.0)
      // that can't parse optional chaining / nullish coalescing. Emitting ES2019
      // strips `?.`/`??` so the app runs there and the landing prerenders.
      target: "es2019",
    },
    server: {
      port: 5173,
    },
  };
});
