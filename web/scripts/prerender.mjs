// Prerenders the public landing ("/") into dist/index.html so the hero paints
// from static HTML (main.tsx hydrates it on "/"). Runs as a postbuild step.
//
// Why not react-snap: it pins an ancient puppeteer whose bundled Chromium fails
// to launch on Vercel's build image ("libnss3.so: cannot open shared object
// file"). @sparticuz/chromium ships a Chromium with its own libraries, built for
// exactly these constrained (Lambda/Vercel) environments.
//
// This step is intentionally best-effort: any failure logs a warning and exits
// 0, so a prerender problem degrades to a normal (un-prerendered) SPA instead of
// breaking the whole deploy. main.tsx handles both cases.
import { createServer } from "node:http";
import { readFile, writeFile } from "node:fs/promises";
import { join, extname } from "node:path";
import { fileURLToPath } from "node:url";

const DIST = fileURLToPath(new URL("../dist", import.meta.url));
const MIME = {
  ".html": "text/html",
  ".js": "text/javascript",
  ".mjs": "text/javascript",
  ".css": "text/css",
  ".svg": "image/svg+xml",
  ".json": "application/json",
  ".woff2": "font/woff2",
  ".woff": "font/woff",
  ".png": "image/png",
  ".ico": "image/x-icon",
  ".txt": "text/plain",
  ".xml": "application/xml",
};

function startStaticServer() {
  const server = createServer(async (req, res) => {
    const requestPath = decodeURIComponent((req.url || "/").split("?")[0]);
    const relative = requestPath === "/" || !extname(requestPath) ? "/index.html" : requestPath;
    try {
      const body = await readFile(join(DIST, relative));
      res.writeHead(200, { "content-type": MIME[extname(relative)] || "application/octet-stream" });
      res.end(body);
    } catch {
      // SPA fallback so any client-side route resolves to the shell.
      try {
        const shell = await readFile(join(DIST, "index.html"));
        res.writeHead(200, { "content-type": "text/html" });
        res.end(shell);
      } catch {
        res.writeHead(404);
        res.end();
      }
    }
  });
  return new Promise((resolve) => {
    server.listen(0, "127.0.0.1", () => resolve(server));
  });
}

async function main() {
  const [{ default: puppeteer }, { default: chromium }] = await Promise.all([
    import("puppeteer-core"),
    import("@sparticuz/chromium"),
  ]);

  const server = await startStaticServer();
  const { port } = server.address();

  const browser = await puppeteer.launch({
    args: chromium.args,
    executablePath: await chromium.executablePath(),
    headless: chromium.headless,
  });

  try {
    const page = await browser.newPage();
    await page.goto(`http://127.0.0.1:${port}/`, {
      waitUntil: "domcontentloaded",
      timeout: 30000,
    });
    // The hero is the proof the app rendered; wait for it before snapshotting.
    await page.waitForSelector(".landing", { timeout: 15000 });
    const html = await page.content();
    await writeFile(join(DIST, "index.html"), html, "utf8");
    console.log("[prerender] Wrote prerendered landing into dist/index.html");
  } finally {
    await browser.close();
    server.close();
  }
}

main().catch((error) => {
  console.warn(
    "[prerender] Skipped (build continues, landing served un-prerendered):",
    error?.message || error,
  );
  process.exit(0);
});
