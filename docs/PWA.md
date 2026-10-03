# Installable PWA (app shell)

The frontend can be installed as a PWA with a precached app shell: fast start in a
standalone window, and the shell still loads offline. Dynamic data is never cached; the
API, Google Sign-In and analytics always go to the network.

It is behind a build-time flag and **off by default**.

## Enable

Set `VITE_PWA_ENABLED=true` on the `verifiko` (frontend) Vercel project and redeploy. The
flag is read at build time, so changing it always needs a new deployment.

With the flag on, the build adds:

- `manifest.webmanifest` and a `<link rel="manifest">` (start URL `/app`, standalone,
  icons in `web/public/pwa-*.png`)
- the iOS `apple-*` meta tags and `apple-touch-icon`
- `sw.js` (Workbox): precaches the files emitted by the build and serves `index.html` for
  in-app navigations; no `runtimeCaching`
- registration from the bundle (`web/src/pwa/registerPwa.ts`), never an inline script,
  because the CSP in `web/vercel.json` does not allow `'unsafe-inline'` scripts

Updates use `registerType: "prompt"`. When a new deployment is detected, the page shows
"A new version of Verifiko is available · Reload". The new worker activates only when the
user clicks Reload, so a running page never has its shell swapped underneath it.

## Rollback (kill switch)

Set `VITE_PWA_ENABLED=false` (or remove it) and redeploy.

With the flag off, the build still emits `/sw.js`, but as a **self-destroying** worker
(`selfDestroying` in vite-plugin-pwa). Nothing registers it, so browsers that never had
the PWA ignore it. Browsers that installed it while the flag was on fetch it on their
next update check: the browser checks on every navigation, and `/sw.js` is served with
`Cache-Control: max-age=0, must-revalidate`. The worker then:

1. activates immediately,
2. unregisters itself,
3. deletes its caches,
4. reloads open tabs, which then load the normal (non-PWA) site from the network.

Do not delete `sw.js` from the deployment as a rollback. A 404 on the update check leaves
the old worker installed and still serving the old cached shell.

For a single machine, you can also do it by hand: DevTools → Application → Service
workers → Unregister, then Storage → Clear site data.

## Verify

- `cd web && VITE_PWA_ENABLED=true npm run build`: `dist/index.html` must contain both the
  `<link rel="manifest">` and the prerendered landing inside `#root`. The prerender
  (`postbuild`) runs after the PWA plugin and only replaces the root marker.
- Chrome DevTools → Application → Manifest shows no installability errors, and → Service
  workers shows `sw.js` activated with scope `/`.
- Network panel: requests to `api.verifiko.es` are never "(ServiceWorker)" and never
  appear in Cache Storage.
