import { Suspense } from "react";
import { renderToString } from "react-dom/server";
import { StaticRouter } from "react-router-dom/server";

import { AuthProvider } from "./lib/auth";
import { I18nProvider } from "./lib/i18n";
import { LandingPage } from "./pages/LandingPage";

// Server-side renders the public landing ("/") to static HTML at build time.
// No browser is involved — unlike react-snap / @sparticuz/chromium, which can't
// launch Chromium on Vercel's build image (libnss3.so is missing there) — so
// this runs anywhere Node runs, and can be verified locally. main.tsx hydrates
// this markup on "/". Providers are SSR-safe: getStoredLanguage() guards on
// `typeof window`, and AuthProvider reads storage only inside an effect (which
// does not run during renderToString), so this renders the default-language,
// signed-out landing — exactly the client's first render on "/".
export function render(): string {
  return renderToString(
    <I18nProvider>
      <AuthProvider>
        <StaticRouter location="/">
          {/* Mirrors the client tree in App.tsx, where "/" renders inside
              <Suspense>. The boundary emits <!--$-->…<!--/$--> markers; without
              them hydrateRoot sees a different structure and discards the
              prerendered HTML (React errors #418/#423). */}
          <Suspense fallback={null}>
            <LandingPage />
          </Suspense>
        </StaticRouter>
      </AuthProvider>
    </I18nProvider>,
  );
}
