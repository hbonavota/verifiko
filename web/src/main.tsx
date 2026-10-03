import React from "react";
import ReactDOM from "react-dom/client";

import App from "./App";
import { AuthProvider } from "./lib/auth";
import { I18nProvider } from "./lib/i18n";
import "./styles/index.css";

const rootElement = document.getElementById("root") as HTMLElement;

// react-snap prerenders only "/" to static HTML. The SPA fallback serves that
// same index.html for every deep link (e.g. /app), so we must hydrate *only* on
// "/" — where the markup matches what React renders. On any other path the
// snapshot is the landing, which would cause a hydration mismatch, so we discard
// it and mount fresh (those routes are behind auth and not perf-critical).
const isLandingSnapshot =
  rootElement.hasChildNodes() && window.location.pathname === "/";

const tree = (
  <React.StrictMode>
    <I18nProvider deferStoredLanguage={isLandingSnapshot}>
      <AuthProvider>
        <App />
      </AuthProvider>
    </I18nProvider>
  </React.StrictMode>
);

if (isLandingSnapshot) {
  ReactDOM.hydrateRoot(rootElement, tree);
} else {
  rootElement.innerHTML = "";
  ReactDOM.createRoot(rootElement).render(tree);
}

// Installable PWA, behind VITE_PWA_ENABLED (a build-time constant): when the flag is
// off this branch and the registration module are dropped from the bundle.
if (__PWA_ENABLED__ && "serviceWorker" in navigator) {
  void import("./pwa/registerPwa").then(({ registerPwa }) => registerPwa());
}
