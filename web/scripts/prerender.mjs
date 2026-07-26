// Injects the server-rendered landing ("/") into dist/index.html as a postbuild
// step, so the hero paints from static HTML (main.tsx hydrates it on "/").
//
// The markup comes from dist-ssr/entry-ssr.js (built with `vite build --ssr`),
// rendered with react-dom/server — no browser, no system libraries. This is the
// only prerender approach that works on Vercel's build image, where Chromium
// (react-snap, @sparticuz/chromium) fails to launch (libnss3.so missing).
//
// Best-effort: any failure logs a warning and exits 0, so the deploy never
// breaks — the landing just serves un-prerendered and main.tsx mounts normally.
import { readFile, writeFile } from "node:fs/promises";
import { join } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const DIST = fileURLToPath(new URL("../dist", import.meta.url));
const SSR_DIR = fileURLToPath(new URL("../dist-ssr", import.meta.url));
const ROOT_MARKER = '<div id="root"></div>';

async function loadRender() {
  for (const name of ["entry-ssr.js", "entry-ssr.mjs"]) {
    try {
      const mod = await import(pathToFileURL(join(SSR_DIR, name)).href);
      if (typeof mod.render === "function") {
        return mod.render;
      }
    } catch {
      // Try the next candidate filename.
    }
  }
  throw new Error("SSR bundle dist-ssr/entry-ssr.js with a render() export was not found");
}

async function main() {
  const render = await loadRender();
  const appHtml = render();
  if (!appHtml || !appHtml.includes("landing")) {
    throw new Error("SSR render produced no landing markup");
  }

  const indexPath = join(DIST, "index.html");
  const html = await readFile(indexPath, "utf8");
  if (!html.includes(ROOT_MARKER)) {
    throw new Error(`Root marker ${ROOT_MARKER} not found in dist/index.html`);
  }

  await writeFile(indexPath, html.replace(ROOT_MARKER, `<div id="root">${appHtml}</div>`), "utf8");
  console.log("[prerender] Injected server-rendered landing into dist/index.html");
}

main().catch((error) => {
  console.warn(
    "[prerender] Skipped (build continues, landing served un-prerendered):",
    error?.message || error,
  );
  process.exit(0);
});
